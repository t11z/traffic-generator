#!/usr/bin/env python3
"""
Simple Selenium-based traffic generator

⚠️ Use responsibly: This script is intended for testing your own sites or
explicitly permitted targets (e.g., staging). Do not use it to inflate ad
impressions, manipulate analytics, or violate a website's Terms of Service.

Features
- Configurable list of targets with individual intervals
- Optional jitter to avoid perfect periodicity
- Per-URL dwell time, optional auto-scroll
- Headless or visible browser
- Basic random User-Agent rotation (optional)
- Special handling for YouTube: watch video until finished
- Graceful shutdown (Ctrl+C)
"""
import argparse
import json
import random
import signal
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Lazy import yaml if available
try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException, JavascriptException

try:
    from webdriver_manager.chrome import ChromeDriverManager  # type: ignore
except Exception:
    ChromeDriverManager = None  # type: ignore

@dataclass
class Target:
    url: str
    interval_seconds: int
    dwell_seconds: int
    jitter_seconds: int = 0
    scroll: bool = True
    next_run: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @staticmethod
    def from_dict(d: Dict[str, Any], defaults: Dict[str, Any]) -> "Target":
        def get(name: str, fallback: Any) -> Any:
            return d.get(name, defaults.get(name, fallback))

        url = d.get("url")
        if not url or not isinstance(url, str):
            raise ValueError("Each target requires a valid 'url' string")
        interval = int(get("interval_seconds", 300))
        dwell = int(get("dwell_seconds", 8))
        jitter = int(get("jitter_seconds", 0))
        scroll = bool(get("scroll", True))
        return Target(url=url, interval_seconds=interval, dwell_seconds=dwell, jitter_seconds=jitter, scroll=scroll)

@dataclass
class Config:
    targets: List[Target]
    user_agents: List[str]

    @staticmethod
    def load(path: Optional[Path]) -> "Config":
        if path is None:
            return Config(targets=[Target(url="https://example.com", interval_seconds=300, dwell_seconds=8)], user_agents=[])

        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        raw: Dict[str, Any]
        if path.suffix.lower() in {".yaml", ".yml"}:
            if yaml is None:
                raise RuntimeError("PyYAML not installed; install with 'pip install pyyaml'")
            with path.open("r", encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}
        else:
            with path.open("r", encoding="utf-8") as f:
                raw = json.load(f)

        defaults = raw.get("defaults", {}) or {}
        user_agents = list(raw.get("user_agents", []) or [])
        targets_raw = raw.get("targets", [])
        if not isinstance(targets_raw, list) or not targets_raw:
            raise ValueError("Config must include a non-empty 'targets' list")

        targets = [Target.from_dict(t, defaults) for t in targets_raw]
        return Config(targets=targets, user_agents=user_agents)

class GracefulExit(Exception):
    pass

def now_utc() -> datetime:
    return datetime.now(timezone.utc)

def log(msg: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

def pick_user_agent(pool: List[str]) -> Optional[str]:
    if not pool:
        return None
    return random.choice(pool)

# --- Browser build (robust Debian handling) ---

def build_driver(headless: bool, user_agent: Optional[str]) -> webdriver.Chrome:
    import shutil, tempfile, atexit
    from selenium.webdriver.chrome.service import Service as ChromeService

    def _make_opts(tmp_root: Path) -> ChromeOptions:
        opts = ChromeOptions()
        if headless:
            opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-extensions")
        opts.add_argument("--no-first-run")
        opts.add_argument("--no-default-browser-check")
        opts.add_argument("--disable-default-apps")
        opts.add_argument("--window-size=1280,800")
        user_dir = tmp_root / "profile"
        cache_dir = tmp_root / "cache"
        media_cache_dir = tmp_root / "media-cache"
        for d in (user_dir, cache_dir, media_cache_dir):
            d.mkdir(parents=True, exist_ok=True)
        opts.add_argument(f"--user-data-dir={user_dir}")
        opts.add_argument("--profile-directory=Default")
        opts.add_argument(f"--disk-cache-dir={cache_dir}")
        opts.add_argument(f"--media-cache-dir={media_cache_dir}")
        opts.add_argument("--remote-debugging-port=0")
        if user_agent:
            opts.add_argument(f"--user-agent={user_agent}")
        if Path("/usr/bin/chromium").exists():
            opts.binary_location = "/usr/bin/chromium"
        elif Path("/usr/bin/chromium-browser").exists():
            opts.binary_location = "/usr/bin/chromium-browser"
        return opts

    def _make_service() -> ChromeService:
        if Path("/usr/bin/chromedriver").exists():
            return ChromeService(executable_path="/usr/bin/chromedriver")
        if ChromeDriverManager is not None:
            driver_path = ChromeDriverManager().install()
            return ChromeService(executable_path=driver_path)
        return ChromeService()

    tmp_root = Path(tempfile.mkdtemp(prefix="trafficgen-chrome-"))
    atexit.register(lambda: shutil.rmtree(tmp_root, ignore_errors=True))
    opts = _make_opts(tmp_root)
    service = _make_service()

    driver = webdriver.Chrome(service=service, options=opts)
    driver.set_page_load_timeout(60)
    return driver

# --- Helpers ---

def auto_scroll(driver: webdriver.Chrome, dwell_seconds: int) -> None:
    start = time.time()
    height = driver.execute_script("return Math.max(document.body.scrollHeight, document.documentElement.scrollHeight);")
    height = max(int(height), 2000)
    positions = [0, int(height * 0.25), int(height * 0.5), int(height * 0.75), height - 1]
    i = 0
    direction = 1
    while time.time() - start < dwell_seconds:
        pos = positions[i]
        driver.execute_script("window.scrollTo(0, arguments[0]);", pos)
        time.sleep(1.0)
        i += direction
        if i >= len(positions):
            i = len(positions) - 2
            direction = -1
        elif i < 0:
            i = 1
            direction = 1

# --- New: YouTube watch handler ---

def is_youtube_url(url: str) -> bool:
    u = url.lower()
    return ("youtube.com/watch" in u) or ("youtu.be/" in u)

def watch_youtube_until_end(driver: webdriver.Chrome, max_wait_seconds: int = 3 * 60 * 60) -> None:
    # Wait for <video>
    video = None
    for _ in range(100):
        try:
            video = driver.find_element(By.TAG_NAME, "video")
            break
        except Exception:
            time.sleep(0.2)
    if not video:
        log("YouTube: no <video> element found; fallback to dwell")
        return

    # Ensure playback (autoplay may be blocked)
    try:
        driver.execute_script("arguments[0].muted = true; arguments[0].play();", video)
    except JavascriptException:
        pass

    # Get duration
    duration = None
    for _ in range(50):
        try:
            duration = driver.execute_script("return arguments[0].duration;", video)
            if duration and duration > 0:
                break
        except Exception:
            pass
        time.sleep(0.2)

    if not duration or duration <= 0:
        log("YouTube: could not read duration; fallback to dwell")
        return

    log(f"YouTube: video length ~ {int(duration)}s")

    start = time.time()
    last_log = 0.0
    while True:
        if time.time() - start > max_wait_seconds:
            log("YouTube: reached safety max_wait, moving on")
            break
        try:
            current = driver.execute_script("return arguments[0].currentTime;", video)
            paused = driver.execute_script("return arguments[0].paused;", video)
            if paused:
                try:
                    driver.execute_script("arguments[0].play();", video)
                except Exception:
                    pass
            if current is not None and duration - float(current) <= 1.0:
                log("YouTube: finished")
                break
            if current is not None and current - last_log >= 15:
                log(f"YouTube: progress {current:.0f}/{duration:.0f}s")
                last_log = current
        except Exception:
            log("YouTube: video element not accessible; assuming finished")
            break
        time.sleep(2)

# --- Main visit function ---

def visit(driver: webdriver.Chrome, target: Target) -> None:
    jitter = random.randint(-target.jitter_seconds, target.jitter_seconds) if target.jitter_seconds > 0 else 0
    log(f"Visiting {target.url} (dwell={target.dwell_seconds}s, jitter={jitter:+d}s)")
    try:
        driver.get(target.url)
        for _ in range(30):
            try:
                state = driver.execute_script("return document.readyState")
                if state == "complete":
                    break
            except Exception:
                pass
            time.sleep(0.2)

        if is_youtube_url(target.url):
            watch_youtube_until_end(driver)
        else:
            if target.scroll:
                auto_scroll(driver, max(1, target.dwell_seconds))
            else:
                time.sleep(max(1, target.dwell_seconds))
    except WebDriverException as e:
        log(f"WARN: Error visiting {target.url}: {e.__class__.__name__}: {e}")
    finally:
        target.next_run = now_utc() + timedelta(seconds=target.interval_seconds + jitter)
        log(f"Next run for {target.url} at {target.next_run.astimezone().strftime('%H:%M:%S')}")

# --- Run loop ---

def run_loop(cfg: Config, headless: bool) -> None:
    ua = pick_user_agent(cfg.user_agents)
    if ua:
        log(f"Using User-Agent: {ua}")
    driver = build_driver(headless=headless, user_agent=ua)

    def _handle_sigint(signum, frame):
        raise GracefulExit()

    signal.signal(signal.SIGINT, _handle_sigint)
    signal.signal(signal.SIGTERM, _handle_sigint)

    for i, t in enumerate(cfg.targets):
        t.next_run = now_utc() + timedelta(seconds=i * 2)

    try:
        while True:
            now = now_utc()
            due = [t for t in cfg.targets if t.next_run <= now]
            if not due:
                next_at = min(t.next_run for t in cfg.targets)
                sleep_s = max(0.5, (next_at - now).total_seconds())
                time.sleep(min(sleep_s, 5.0))
                continue
            for t in sorted(due, key=lambda x: x.next_run):
                visit(driver, t)
    except GracefulExit:
        log("Shutting down...")
    finally:
        try:
            driver.quit()
        except Exception:
            pass

# --- Entry point ---

def main() -> None:
    parser = argparse.ArgumentParser(description="Simple Selenium traffic generator")
    parser.add_argument("--config", type=str, default=None, help="Path to YAML/JSON config file")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode (default)")
    parser.add_argument("--headed", action="store_true", help="Run with a visible browser window")
    args = parser.parse_args()

    headless = True
    if args.headed:
        headless = False
    elif args.headless:
        headless = True

    cfg = Config.load(Path(args.config) if args.config else None)
    if not cfg.targets:
        print("No targets configured.")
        sys.exit(1)

    log(f"Loaded {len(cfg.targets)} targets.")
    run_loop(cfg, headless=headless)

if __name__ == "__main__":
    main()
