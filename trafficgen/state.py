"""Thread-safe run/target state shared between the worker and the TUI.

The worker thread mutates this state through methods (all guarded by a single
lock); the renderer only reads snapshots, so the live display never races with
the scheduler. No Selenium import — pure, testable.
"""
from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Deque, List, Optional


class Status:
    IDLE = "idle"
    LOADING = "loading"
    WATCHING = "watching"
    SCROLLING = "scrolling"
    ACTING = "acting"
    WAITING = "waiting"
    ERROR = "error"


@dataclass
class TargetState:
    url: str
    status: str = Status.IDLE
    activity: str = ""
    progress: Optional[float] = None  # 0..1 or None when not applicable
    next_run: Optional[datetime] = None
    visits: int = 0
    errors: int = 0
    last_error: str = ""


@dataclass
class TargetSnapshot:
    url: str
    status: str
    activity: str
    progress: Optional[float]
    next_run: Optional[datetime]
    visits: int
    errors: int
    last_error: str


class RunState:
    def __init__(self, urls: List[str], log_capacity: int = 200) -> None:
        self._lock = threading.Lock()
        self.started_at = datetime.now(timezone.utc)
        self.user_agent: Optional[str] = None
        self.driver_rebuilds = 0
        self._targets = {u: TargetState(url=u) for u in urls}
        self._order = list(urls)
        self._log: Deque[str] = deque(maxlen=log_capacity)

    # --- mutations (locked) ---
    def set_user_agent(self, ua: Optional[str]) -> None:
        with self._lock:
            self.user_agent = ua

    def note_rebuild(self) -> None:
        with self._lock:
            self.driver_rebuilds += 1

    def update(
        self,
        url: str,
        *,
        status: Optional[str] = None,
        activity: Optional[str] = None,
        progress: Optional[float] = ...,  # type: ignore[assignment]
        next_run: Optional[datetime] = ...,  # type: ignore[assignment]
    ) -> None:
        with self._lock:
            ts = self._targets.get(url)
            if ts is None:
                return
            if status is not None:
                ts.status = status
            if activity is not None:
                ts.activity = activity
            if progress is not ...:
                ts.progress = progress  # type: ignore[assignment]
            if next_run is not ...:
                ts.next_run = next_run  # type: ignore[assignment]

    def record_visit(self, url: str) -> None:
        with self._lock:
            ts = self._targets.get(url)
            if ts:
                ts.visits += 1

    def record_error(self, url: str, message: str) -> None:
        with self._lock:
            ts = self._targets.get(url)
            if ts:
                ts.errors += 1
                ts.last_error = message
                ts.status = Status.ERROR

    def add_log(self, line: str) -> None:
        with self._lock:
            self._log.append(line)

    # --- reads (locked, returns copies) ---
    def snapshot_targets(self) -> List[TargetSnapshot]:
        with self._lock:
            return [
                TargetSnapshot(
                    url=ts.url, status=ts.status, activity=ts.activity,
                    progress=ts.progress, next_run=ts.next_run,
                    visits=ts.visits, errors=ts.errors, last_error=ts.last_error,
                )
                for ts in (self._targets[u] for u in self._order)
            ]

    def snapshot_log(self) -> List[str]:
        with self._lock:
            return list(self._log)

    def snapshot_meta(self) -> dict:
        with self._lock:
            return {
                "started_at": self.started_at,
                "user_agent": self.user_agent,
                "driver_rebuilds": self.driver_rebuilds,
            }
