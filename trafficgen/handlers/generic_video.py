"""Generic <video> handler usable for any site via an explicit ``handler: generic_video``."""
from __future__ import annotations

from .base import HandlerContext
from ._video import watch_video


def generic_video_handler(ctx: HandlerContext) -> None:
    watch_video(ctx, label="video")
