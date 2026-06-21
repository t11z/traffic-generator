"""Small browser interactions shared by handlers and actions.

These talk to a Selenium WebDriver but only via ``execute_script`` / generic
methods, so no Selenium import is required here.
"""
from __future__ import annotations

import time
from typing import Any, Callable, Optional


def wait_ready(driver: Any, timeout: float = 6.0) -> None:
    """Wait until ``document.readyState === 'complete'`` (best effort)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if driver.execute_script("return document.readyState") == "complete":
                return
        except Exception:
            pass
        time.sleep(0.2)


def auto_scroll(
    driver: Any,
    dwell_seconds: int,
    passes: int = 0,
    report_progress: Optional[Callable[[Optional[float], str], None]] = None,
    should_stop: Optional[Callable[[], bool]] = None,
) -> None:
    """Scroll up and down the page for ``dwell_seconds``.

    If ``passes`` > 0 the dwell is interpreted as roughly ``passes`` full
    oscillations instead of a wall-clock budget (whichever finishes first still
    respects ``dwell_seconds`` as an upper bound when given).
    """
    start = time.time()
    try:
        height = driver.execute_script(
            "return Math.max(document.body.scrollHeight, "
            "document.documentElement.scrollHeight);"
        )
    except Exception:
        height = 2000
    height = max(int(height or 0), 2000)
    positions = [0, int(height * 0.25), int(height * 0.5), int(height * 0.75), height - 1]

    i = 0
    direction = 1
    steps_done = 0
    total_steps = passes * len(positions) if passes > 0 else 0
    while True:
        if should_stop and should_stop():
            return
        elapsed = time.time() - start
        if dwell_seconds and elapsed >= dwell_seconds:
            break
        if passes > 0 and steps_done >= total_steps:
            break
        try:
            driver.execute_script("window.scrollTo(0, arguments[0]);", positions[i])
        except Exception:
            pass
        if report_progress is not None:
            if dwell_seconds:
                frac = min(1.0, elapsed / dwell_seconds)
            elif total_steps:
                frac = min(1.0, steps_done / total_steps)
            else:
                frac = None
            report_progress(frac, "scrolling")
        time.sleep(1.0)
        steps_done += 1
        i += direction
        if i >= len(positions):
            i = len(positions) - 2
            direction = -1
        elif i < 0:
            i = 1
            direction = 1
