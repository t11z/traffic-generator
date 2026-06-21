import pytest

from trafficgen.actions import build_action, valid_action_types
from trafficgen.actions.builtins import (
    ClickRandomLinkAction,
    RandomWalkAction,
    ScrollAction,
    SearchAction,
    WaitAction,
)


def test_valid_action_types():
    types = valid_action_types()
    for t in ("scroll", "wait", "click_random_link", "random_walk", "search"):
        assert t in types


def test_build_scroll():
    a = build_action({"type": "scroll", "passes": 3, "dwell": 12})
    assert isinstance(a, ScrollAction)
    assert a.passes == 3
    assert a.dwell == 12


def test_build_wait():
    a = build_action({"type": "wait", "seconds": 7, "jitter": 2})
    assert isinstance(a, WaitAction)
    assert a.seconds == 7
    assert a.jitter == 2


def test_build_random_walk():
    a = build_action({"type": "random_walk", "hops": 4, "dwell": 6, "same_domain": False})
    assert isinstance(a, RandomWalkAction)
    assert a.hops == 4
    assert a.dwell_per_hop == 6
    assert a.same_domain_only is False


def test_build_search_and_click():
    s = build_action({"type": "search", "query": "hello", "selector": "#q"})
    assert isinstance(s, SearchAction)
    assert s.query == "hello"
    c = build_action({"type": "click_random_link", "same_origin": False})
    assert isinstance(c, ClickRandomLinkAction)
    assert c.same_origin is False


def test_unknown_type_raises():
    with pytest.raises(ValueError) as exc:
        build_action({"type": "bogus"})
    assert "bogus" in str(exc.value)


def test_missing_type_raises():
    with pytest.raises(ValueError):
        build_action({"passes": 1})
