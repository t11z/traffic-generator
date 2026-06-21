"""Handler registry wiring. Importing this package registers all handlers."""
from __future__ import annotations

from ..urlmatch import is_twitch_url, is_vimeo_url, is_youtube_url
from .base import Handler, HandlerContext
from .registry import dispatch, known_handlers, register_handler, set_default_handler

from .default import default_handler
from .generic_video import generic_video_handler
from .infinite_scroll import infinite_scroll_handler
from .twitch import twitch_handler
from .vimeo import vimeo_handler
from .youtube import youtube_handler


def _register_all() -> None:
    set_default_handler(default_handler)
    register_handler("youtube", is_youtube_url, youtube_handler, priority=100)
    register_handler("vimeo", is_vimeo_url, vimeo_handler, priority=90)
    register_handler("twitch", is_twitch_url, twitch_handler, priority=90)
    # generic_video and infinite_scroll are opt-in via `handler:` (no matcher),
    # registered by name so dispatch can find them.
    register_handler("generic_video", lambda url: False, generic_video_handler, priority=0)
    register_handler("infinite_scroll", lambda url: False, infinite_scroll_handler, priority=0)


_register_all()

__all__ = [
    "Handler",
    "HandlerContext",
    "dispatch",
    "known_handlers",
    "register_handler",
]
