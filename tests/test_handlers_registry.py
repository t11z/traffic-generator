import pytest

from trafficgen.handlers import dispatch, known_handlers
from trafficgen.handlers.registry import register_handler


def test_dispatch_youtube():
    h = dispatch("https://www.youtube.com/watch?v=abc")
    assert h.__name__ == "youtube_handler"


def test_dispatch_vimeo():
    assert dispatch("https://vimeo.com/123").__name__ == "vimeo_handler"


def test_dispatch_unmatched_returns_default():
    assert dispatch("https://example.com/page").__name__ == "default_handler"


def test_explicit_handler_overrides_matcher():
    # URL looks like YouTube, but explicit handler name wins
    h = dispatch("https://www.youtube.com/watch?v=abc", explicit_name="default")
    assert h.__name__ == "default_handler"


def test_explicit_unknown_handler_raises():
    with pytest.raises(ValueError):
        dispatch("https://example.com", explicit_name="nope")


def test_known_handlers_contains_builtins():
    names = known_handlers()
    for n in ("default", "youtube", "vimeo", "twitch", "generic_video", "infinite_scroll"):
        assert n in names


def test_priority_ordering():
    marker = "https://priority-test.invalid/x"
    match = lambda u: u == marker  # noqa: E731 - only matches our unique URL
    register_handler("prio_low", match, lambda ctx: "low", priority=1)
    register_handler("prio_high", match, lambda ctx: "high", priority=50)
    h = dispatch(marker)
    assert h(None) == "high"
