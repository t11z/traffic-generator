"""Generic HTML5 ``<video>`` watcher shared by the video handlers.

Works for any page exposing a ``<video>`` element. Handlers can inject an
optional consent step (run once before playback) and a per-iteration hook
(e.g. to skip ads). Designed to survive headless throttling: it finishes when
the player reaches the end OR, in wall-clock mode, when wall time exceeds the
duration plus a small buffer.
"""
from __future__ import annotations

import time
from typing import Callable, Optional

from .base import HandlerContext

# JS snippets operating on the first <video> on the page.
_JS_DUR = "var v=document.querySelector('video'); return v? v.duration : 0;"
_JS_TIME = "var v=document.querySelector('video'); return v? v.currentTime : 0;"
_JS_PAUSED = "var v=document.querySelector('video'); return v? v.paused : true;"
_JS_PLAY = (
    "var v=document.querySelector('video');"
    "if(v){v.muted=true; try{v.play();}catch(e){}} return true;"
)
_JS_RATE = (
    "var v=document.querySelector('video');"
    "if(v){v.playbackRate=1.0; v.defaultPlaybackRate=1.0;} return true;"
)
_JS_UNHIDE = (
    "try{Object.defineProperty(document,'hidden',{get:()=>false});}catch(e){}"
    "try{Object.defineProperty(document,'visibilityState',{get:()=>'visible'});}catch(e){}"
    "try{document.hasFocus=()=>true;}catch(e){}"
    "true;"
)


def _safe_script(driver, js, default=None):
    try:
        return driver.execute_script(js)
    except Exception:
        return default


def watch_video(
    ctx: HandlerContext,
    *,
    label: str = "video",
    consent_fn: Optional[Callable[[HandlerContext], None]] = None,
    iteration_fn: Optional[Callable[[HandlerContext], bool]] = None,
    max_wait_seconds: int = 3 * 60 * 60,
) -> None:
    """Play the page's ``<video>`` until it ends.

    ``iteration_fn`` is called every loop; if it returns ``True`` the elapsed
    iteration is treated as "ad time" and not counted toward progress.
    """
    driver = ctx.driver
    wallclock = bool(getattr(ctx.settings, "yt_wallclock", False))

    if consent_fn is not None:
        try:
            consent_fn(ctx)
        except Exception:
            pass

    # Wait for a <video> element to appear.
    found = False
    for _ in range(150):
        if ctx.should_stop():
            return
        if _safe_script(driver, "return !!document.querySelector('video');", False):
            found = True
            break
        time.sleep(0.2)
    if not found:
        ctx.log(f"{label}: no <video> element found; fallback to dwell")
        return

    _safe_script(driver, _JS_UNHIDE)
    _safe_script(driver, _JS_PLAY)
    _safe_script(driver, _JS_RATE)

    duration = None
    for _ in range(100):
        if ctx.should_stop():
            return
        d = _safe_script(driver, _JS_DUR)
        try:
            if d and float(d) > 0:
                duration = float(d)
                break
        except Exception:
            pass
        time.sleep(0.2)
    if not duration or duration <= 0:
        ctx.log(f"{label}: could not read duration; fallback to dwell")
        return

    ctx.log(f"{label}: length ~ {int(duration)}s")
    start = time.time()
    last_log = start
    last_time = 0.0
    target_end = start + duration + 1.0

    while True:
        if ctx.should_stop():
            return
        now = time.time()
        if now - start > max_wait_seconds:
            ctx.log(f"{label}: reached safety max_wait, moving on")
            return

        ad_active = False
        if iteration_fn is not None:
            try:
                ad_active = bool(iteration_fn(ctx))
            except Exception:
                ad_active = False

        current = _safe_script(driver, _JS_TIME, 0.0) or 0.0
        try:
            current = float(current)
        except Exception:
            current = 0.0
        paused = bool(_safe_script(driver, _JS_PAUSED, False))

        advanced = current - last_time
        if paused or advanced < 0.25:
            _safe_script(driver, _JS_UNHIDE)
            _safe_script(driver, _JS_RATE)
            _safe_script(driver, _JS_PLAY)
            _safe_script(driver, "document.querySelector('video')?.click();")
            _safe_script(driver, "document.body.dispatchEvent(new KeyboardEvent('keydown',{key:'k'}));")

        if not ad_active:
            finished_player = (duration - current) <= 1.0
            finished_wall = wallclock and (now >= target_end)
            frac = max(0.0, min(1.0, current / duration))
            ctx.report_progress(frac, f"{label} {int(current)}/{int(duration)}s")
            if finished_player or finished_wall:
                ctx.log(f"{label}: finished")
                return
        else:
            ctx.report_progress(None, f"{label}: ad")

        if now - last_log >= 15:
            ctx.log(
                f"{label}: progress wall={int(now - start)}/{int(duration)}s "
                f"player={int(current)}/{int(duration)}s"
            )
            last_log = now

        last_time = current
        time.sleep(2)
