"""YouTube handler: cookie consent, ad skipping, watch until the end."""
from __future__ import annotations

from .base import HandlerContext
from ._video import watch_video

_CONSENT_SELECTORS = [
    "button[aria-label*='Accept all']",
    "button[aria-label*='Accept the use']",
    "tp-yt-paper-button[aria-label*='Accept all']",
    "ytd-button-renderer:has(button[aria-label*='Accept'])",
]
_CONSENT_TEXTS = ["accept all", "i agree", "alle akzeptieren", "ich stimme zu"]

_SKIP_SELECTORS = [
    ".ytp-ad-skip-button",
    ".ytp-ad-skip-button-modern",
    ".ytp-skip-ad-button",
    "button.ytp-ad-skip-button-modern",
]


def _accept_consent(ctx: HandlerContext) -> None:
    from selenium.webdriver.common.by import By

    driver = ctx.driver

    def _try_in_current_context() -> bool:
        for sel in _CONSENT_SELECTORS:
            try:
                for el in driver.find_elements(By.CSS_SELECTOR, sel):
                    if el.is_displayed():
                        el.click()
                        ctx.log("YouTube: consent accepted")
                        return True
            except Exception:
                continue
        # text-based fallback
        try:
            for btn in driver.find_elements(By.TAG_NAME, "button"):
                label = (btn.text or "").strip().lower()
                if any(t in label for t in _CONSENT_TEXTS) and btn.is_displayed():
                    btn.click()
                    ctx.log("YouTube: consent accepted (text match)")
                    return True
        except Exception:
            pass
        return False

    if _try_in_current_context():
        return

    # consent may live in an iframe
    try:
        frames = driver.find_elements(By.CSS_SELECTOR, "iframe[src*='consent']")
    except Exception:
        frames = []
    for frame in frames:
        try:
            driver.switch_to.frame(frame)
            handled = _try_in_current_context()
        except Exception:
            handled = False
        finally:
            try:
                driver.switch_to.default_content()
            except Exception:
                pass
        if handled:
            return


def _skip_ads(ctx: HandlerContext) -> bool:
    """Click any visible skip button. Returns True if an ad is currently showing."""
    from selenium.webdriver.common.by import By

    driver = ctx.driver
    ad_showing = False
    try:
        ad_showing = bool(
            driver.execute_script(
                "return !!document.querySelector('.ad-showing, .ytp-ad-player-overlay, "
                ".ytp-ad-player-overlay-layout');"
            )
        )
    except Exception:
        ad_showing = False

    if ad_showing:
        for sel in _SKIP_SELECTORS:
            try:
                for el in driver.find_elements(By.CSS_SELECTOR, sel):
                    if el.is_displayed():
                        el.click()
                        ctx.log("YouTube: skipped ad")
                        return False
            except Exception:
                continue
    return ad_showing


def youtube_handler(ctx: HandlerContext) -> None:
    watch_video(
        ctx,
        label="YouTube",
        consent_fn=_accept_consent,
        iteration_fn=_skip_ads,
    )
