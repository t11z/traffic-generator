import random
from datetime import timedelta

from trafficgen.config import Target
from trafficgen.scheduler import (
    compute_next_run,
    compute_sleep,
    due_targets,
    jitter_for,
    now_utc,
)


def _t(url, interval=100, jitter=0, offset=0):
    t = Target(url=url, interval_seconds=interval, dwell_seconds=5, jitter_seconds=jitter)
    t.next_run = now_utc() + timedelta(seconds=offset)
    return t


def test_due_targets_selects_and_sorts():
    now = now_utc()
    a = _t("a", offset=-10)
    b = _t("b", offset=-5)
    c = _t("c", offset=+30)
    due = due_targets([c, b, a], now)
    assert [t.url for t in due] == ["a", "b"]  # past targets, earliest first


def test_compute_sleep_clamps_high():
    now = now_utc()
    t = _t("a", offset=3600)  # far future
    assert compute_sleep([t], now) == 5.0


def test_compute_sleep_clamps_low():
    now = now_utc()
    t = _t("a", offset=-100)  # overdue
    assert compute_sleep([t], now) == 0.5


def test_compute_sleep_empty():
    assert compute_sleep([], now_utc()) == 5.0


def test_jitter_bounds_deterministic():
    rng = random.Random(42)
    t = _t("a", jitter=15)
    for _ in range(50):
        j = jitter_for(t, rng)
        assert -15 <= j <= 15


def test_jitter_zero():
    t = _t("a", jitter=0)
    assert jitter_for(t) == 0


def test_compute_next_run():
    now = now_utc()
    t = _t("a", interval=100)
    nxt = compute_next_run(t, now, jitter=5)
    assert abs((nxt - now).total_seconds() - 105) < 0.001
