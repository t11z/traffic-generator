"""Infinite-scroll handler: repeatedly scroll to the bottom to trigger loads."""
from __future__ import annotations

import time

from .base import HandlerContext


def infinite_scroll_handler(ctx: HandlerContext) -> None:
    driver = ctx.driver
    dwell = max(2, int(getattr(ctx.target, "dwell_seconds", 30)))
    start = time.time()
    last_height = 0
    while time.time() - start < dwell:
        if ctx.should_stop():
            return
        try:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        except Exception:
            pass
        elapsed = time.time() - start
        ctx.report_progress(min(1.0, elapsed / dwell), "infinite scroll")
        time.sleep(1.5)
        try:
            height = driver.execute_script("return document.body.scrollHeight;") or 0
        except Exception:
            height = last_height
        # nudge back up a little to look organic when no new content loaded
        if height == last_height:
            try:
                driver.execute_script("window.scrollBy(0, -400);")
            except Exception:
                pass
        last_height = height
