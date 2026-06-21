"""Vimeo handler: accept consent, play the embedded <video> to the end."""
from __future__ import annotations

from .base import HandlerContext
from ._video import watch_video


def _accept_consent(ctx: HandlerContext) -> None:
    from selenium.webdriver.common.by import By

    selectors = [
        "#onetrust-accept-btn-handler",
        "button[aria-label*='Accept']",
        "button.accept",
    ]
    for sel in selectors:
        try:
            for el in ctx.driver.find_elements(By.CSS_SELECTOR, sel):
                if el.is_displayed():
                    el.click()
                    ctx.log("Vimeo: consent accepted")
                    return
        except Exception:
            continue


def vimeo_handler(ctx: HandlerContext) -> None:
    watch_video(ctx, label="Vimeo", consent_fn=_accept_consent)
