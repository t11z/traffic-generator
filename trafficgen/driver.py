"""Chromium driver construction and lifecycle (the only heavy Selenium module)."""
from __future__ import annotations

import atexit
import shutil
import tempfile
from pathlib import Path
from typing import Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService

try:
    from webdriver_manager.chrome import ChromeDriverManager  # type: ignore
except Exception:  # pragma: no cover
    ChromeDriverManager = None  # type: ignore

from .config import Settings


def _make_opts(tmp_root: Path, settings: Settings, user_agent: Optional[str]) -> ChromeOptions:
    opts = ChromeOptions()
    if settings.headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--no-first-run")
    opts.add_argument("--no-default-browser-check")
    opts.add_argument("--disable-default-apps")
    opts.add_argument(f"--window-size={settings.window_size}")
    # Allow autoplay + keep player active in service contexts
    opts.add_argument("--autoplay-policy=no-user-gesture-required")
    opts.add_argument("--mute-audio")
    # Reduce background throttling effects in headless/service mode
    opts.add_argument("--disable-background-timer-throttling")
    opts.add_argument("--disable-backgrounding-occluded-windows")
    opts.add_argument("--disable-renderer-backgrounding")
    opts.add_argument("--remote-debugging-port=0")
    if settings.ignore_cert_errors:
        opts.add_argument("--ignore-certificate-errors")
        opts.add_argument("--allow-insecure-localhost")
        try:
            opts.set_capability("acceptInsecureCerts", True)
        except Exception:
            pass
    user_dir = tmp_root / "profile"
    cache_dir = tmp_root / "cache"
    media_cache_dir = tmp_root / "media-cache"
    for d in (user_dir, cache_dir, media_cache_dir):
        d.mkdir(parents=True, exist_ok=True)
    opts.add_argument(f"--user-data-dir={user_dir}")
    opts.add_argument("--profile-directory=Default")
    opts.add_argument(f"--disk-cache-dir={cache_dir}")
    opts.add_argument(f"--media-cache-dir={media_cache_dir}")
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


def build_driver(settings: Settings, user_agent: Optional[str]) -> webdriver.Chrome:
    tmp_root = Path(tempfile.mkdtemp(prefix="trafficgen-chrome-"))
    atexit.register(lambda: shutil.rmtree(tmp_root, ignore_errors=True))
    opts = _make_opts(tmp_root, settings, user_agent)
    service = _make_service()
    driver = webdriver.Chrome(service=service, options=opts)
    driver.set_page_load_timeout(settings.page_load_timeout)
    return driver
