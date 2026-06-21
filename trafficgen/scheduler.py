"""Scheduling math (pure, testable) and the browser worker loop."""
from __future__ import annotations

import random
import time
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from .config import Config, Settings, Target
from .handlers import HandlerContext, dispatch
from .logging_util import log
from .state import RunState, Status


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


# --- Pure scheduling helpers (no Selenium, unit-tested) ---

def due_targets(targets: List[Target], now: datetime) -> List[Target]:
    return sorted([t for t in targets if t.next_run <= now], key=lambda x: x.next_run)


def compute_sleep(targets: List[Target], now: datetime, lo: float = 0.5, hi: float = 5.0) -> float:
    if not targets:
        return hi
    next_at = min(t.next_run for t in targets)
    return min(max(lo, (next_at - now).total_seconds()), hi)


def jitter_for(target: Target, rng: Optional[random.Random] = None) -> int:
    if target.jitter_seconds <= 0:
        return 0
    r = rng or random
    return r.randint(-target.jitter_seconds, target.jitter_seconds)


def compute_next_run(target: Target, now: datetime, jitter: int) -> datetime:
    return now + timedelta(seconds=target.interval_seconds + jitter)


# --- Worker (Selenium) ---

_FATAL_SESSION_MARKERS = (
    "invalid session id",
    "session deleted",
    "no such window",
    "disconnected",
    "chrome not reachable",
    "unable to connect to renderer",
    "tab crashed",
)


def _is_fatal_session_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(m in msg for m in _FATAL_SESSION_MARKERS)


class Worker:
    """Owns the single driver, runs the scheduler, and self-heals on crashes."""

    def __init__(self, cfg: Config, settings: Settings, state: RunState, stop_event) -> None:
        from .driver import build_driver  # local import keeps module light

        self.cfg = cfg
        self.settings = settings
        self.state = state
        self.stop_event = stop_event
        self._build_driver = build_driver
        self.user_agent = random.choice(cfg.user_agents) if cfg.user_agents else None
        self.driver = None
        self._max_rebuilds = 10

    # -- driver lifecycle --
    def _ensure_driver(self):
        if self.driver is None:
            self.driver = self._build_driver(self.settings, self.user_agent)
        return self.driver

    def _rebuild_driver(self):
        try:
            if self.driver is not None:
                self.driver.quit()
        except Exception:
            pass
        self.driver = None
        self.state.note_rebuild()
        log("Worker: rebuilding browser after fatal session error")
        return self._ensure_driver()

    # -- navigation with retry/backoff --
    def _navigate(self, target: Target) -> bool:
        from selenium.common.exceptions import WebDriverException

        attempts = max(1, self.settings.max_retries)
        for attempt in range(1, attempts + 1):
            if self.stop_event.is_set():
                return False
            try:
                self._ensure_driver().get(target.url)
                return True
            except WebDriverException as e:
                if _is_fatal_session_error(e):
                    self.state.record_error(target.url, f"{e.__class__.__name__}: fatal session")
                    if self.state.snapshot_meta()["driver_rebuilds"] < self._max_rebuilds:
                        self._rebuild_driver()
                    else:
                        log("Worker: rebuild cap reached; giving up this cycle")
                        return False
                log(f"WARN: load attempt {attempt}/{attempts} failed for {target.url}: "
                    f"{e.__class__.__name__}")
                if attempt < attempts:
                    backoff = (self.settings.retry_backoff ** (attempt - 1))
                    backoff += random.uniform(0, 0.5)
                    self._sleep_interruptible(min(backoff, 30.0))
        self.state.record_error(target.url, "navigation failed after retries")
        return False

    def _sleep_interruptible(self, seconds: float) -> None:
        end = time.time() + seconds
        while time.time() < end and not self.stop_event.is_set():
            time.sleep(min(0.5, max(0.0, end - time.time())))

    # -- single visit --
    def visit(self, target: Target) -> None:
        from .browser_helpers import wait_ready

        url = target.url
        jitter = jitter_for(target)
        log(f"Visiting {url} (dwell={target.dwell_seconds}s, jitter={jitter:+d}s)")
        self.state.update(url, status=Status.LOADING, activity="loading", progress=None)

        try:
            if not self._navigate(target):
                return
            wait_ready(self._ensure_driver(), timeout=6.0)

            def report(frac, text):
                self.state.update(url, progress=frac, activity=text)

            self.state.update(url, status=Status.WATCHING, activity="visiting")
            ctx = HandlerContext(
                driver=self.driver,
                target=target,
                settings=self.settings,
                log=log,
                report_progress=report,
                stop_event=self.stop_event,
            )
            handler = dispatch(url, target.handler)
            handler(ctx)
            self.state.record_visit(url)
            self.state.update(url, status=Status.WAITING, progress=None, activity="done")
        except Exception as e:  # never let one target kill the loop
            log(f"WARN: Error visiting {url}: {e.__class__.__name__}: {e}")
            self.state.record_error(url, f"{e.__class__.__name__}: {e}")
            if _is_fatal_session_error(e) and \
                    self.state.snapshot_meta()["driver_rebuilds"] < self._max_rebuilds:
                try:
                    self._rebuild_driver()
                except Exception:
                    pass
        finally:
            target.next_run = compute_next_run(target, now_utc(), jitter)
            self.state.update(url, next_run=target.next_run)
            log(f"Next run for {url} at {target.next_run.astimezone().strftime('%H:%M:%S')}")

    # -- main loop --
    def run(self, once: bool = False) -> None:
        self.state.set_user_agent(self.user_agent)
        if self.user_agent:
            log(f"Using User-Agent: {self.user_agent}")
        try:
            self._ensure_driver()
        except Exception as e:
            log(f"FATAL: could not start browser: {e.__class__.__name__}: {e}")
            return

        for i, t in enumerate(self.cfg.targets):
            t.next_run = now_utc() + timedelta(seconds=i * 2)
            self.state.update(t.url, next_run=t.next_run, status=Status.WAITING)

        try:
            if once:
                self._run_once()
            else:
                self._run_forever()
        finally:
            try:
                if self.driver is not None:
                    self.driver.quit()
            except Exception:
                pass

    def _run_forever(self) -> None:
        while not self.stop_event.is_set():
            now = now_utc()
            due = due_targets(self.cfg.targets, now)
            if not due:
                self._sleep_interruptible(compute_sleep(self.cfg.targets, now))
                continue
            for t in due:
                if self.stop_event.is_set():
                    break
                self.visit(t)

    def _run_once(self) -> None:
        """Visit each target exactly once (respecting initial offsets), then stop."""
        for t in sorted(self.cfg.targets, key=lambda x: x.next_run):
            if self.stop_event.is_set():
                return
            wait = (t.next_run - now_utc()).total_seconds()
            if wait > 0:
                self._sleep_interruptible(wait)
            self.visit(t)
