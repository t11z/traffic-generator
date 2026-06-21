"""Pure URL matching helpers (no Selenium import, fully unit-testable)."""
from __future__ import annotations

from urllib.parse import urlparse


def _host(url: str) -> str:
    try:
        netloc = urlparse(url).netloc.lower()
    except Exception:
        return ""
    # strip credentials and port
    if "@" in netloc:
        netloc = netloc.rsplit("@", 1)[1]
    if ":" in netloc:
        netloc = netloc.split(":", 1)[0]
    return netloc


def registrable_domain(url: str) -> str:
    """Return a best-effort registrable domain (last two labels).

    Not a full public-suffix implementation, but good enough for same-domain
    random walks (``www.example.com`` and ``example.com`` compare equal).
    """
    host = _host(url)
    if not host:
        return ""
    parts = host.split(".")
    if len(parts) <= 2:
        return host
    return ".".join(parts[-2:])


def same_domain(a: str, b: str) -> bool:
    da, db = registrable_domain(a), registrable_domain(b)
    return bool(da) and da == db


def is_youtube_url(url: str) -> bool:
    u = url.lower()
    return ("youtube.com/watch" in u) or ("youtu.be/" in u)


def is_vimeo_url(url: str) -> bool:
    host = _host(url)
    return host == "vimeo.com" or host.endswith(".vimeo.com")


def is_twitch_url(url: str) -> bool:
    host = _host(url)
    return host == "twitch.tv" or host.endswith(".twitch.tv")
