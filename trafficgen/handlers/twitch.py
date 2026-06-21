"""Twitch handler: accept consent/mature warning, then watch the stream/VOD.

Live streams have no finite duration, so the watch falls back to the target's
``dwell_seconds`` budget via the generic watcher's safety paths.
"""
from __future__ import annotations

from .base import HandlerContext
from ._video import watch_video


def _accept_consent(ctx: HandlerContext) -> None:
    from selenium.webdriver.common.by import By

    selectors = [
        "button[data-a-target='consent-banner-accept']",
        "button[data-a-target='player-overlay-mature-accept']",
        "button[aria-label*='Accept']",
    ]
    for sel in selectors:
        try:
            for el in ctx.driver.find_elements(By.CSS_SELECTOR, sel):
                if el.is_displayed():
                    el.click()
                    ctx.log("Twitch: dismissed overlay")
        except Exception:
            continue


def twitch_handler(ctx: HandlerContext) -> None:
    # Live streams report Infinity/NaN duration; the watcher will fall back to
    # dwell behaviour by reporting "could not read duration".
    dwell = max(1, int(getattr(ctx.target, "dwell_seconds", 30)))
    watch_video(ctx, label="Twitch", consent_fn=_accept_consent, max_wait_seconds=dwell)
