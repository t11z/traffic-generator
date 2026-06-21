#!/usr/bin/env python3
"""Render the TUI dashboard with mock data to a PNG "screenshot".

Used to generate docs/tui-dashboard.png for the README. Regenerate with::

    python3 scripts/tui_demo.py

Rendering to a raster PNG (rather than embedding rich's SVG) keeps the
monospace grid pixel-accurate on GitHub, which does not load the external
web font the SVG references. Requires ``cairosvg`` (doc/dev tooling only, not a
runtime dependency): ``pip install cairosvg``.
"""
from __future__ import annotations

import sys
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from rich.console import Console  # noqa: E402

from trafficgen.scheduler import now_utc  # noqa: E402
from trafficgen.state import RunState, Status  # noqa: E402
from trafficgen.tui import _render  # noqa: E402


def build_mock_state() -> RunState:
    urls = [
        "https://example.com",
        "https://news.ycombinator.com",
        "https://en.wikipedia.org/wiki/Special:Random",
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://vimeo.com/76979871",
        "https://blog.python.org",
    ]
    st = RunState(urls)
    st.set_user_agent("Mozilla/5.0 (X11; Linux x86_64) Chrome/124.0.0.0 Safari/537.36")
    st.driver_rebuilds = 1
    now = now_utc()

    st.update(urls[0], status=Status.WAITING, activity="done", progress=None,
              next_run=now + timedelta(seconds=42))
    for _ in range(7):
        st.record_visit(urls[0])

    st.update(urls[1], status=Status.SCROLLING, activity="scrolling", progress=0.6,
              next_run=now + timedelta(seconds=118))
    for _ in range(3):
        st.record_visit(urls[1])

    st.update(urls[2], status=Status.ACTING, activity="click_random_link", progress=None,
              next_run=now + timedelta(seconds=205))
    st.record_visit(urls[2])

    st.update(urls[3], status=Status.WATCHING, activity="YouTube 78/213s", progress=0.366,
              next_run=now + timedelta(seconds=1772))
    for _ in range(2):
        st.record_visit(urls[3])

    st.update(urls[4], status=Status.LOADING, activity="loading", progress=None,
              next_run=now + timedelta(seconds=12))

    st.update(urls[5], status=Status.ERROR, activity="done", progress=None,
              next_run=now + timedelta(seconds=300))
    st.record_error(urls[5], "TimeoutException: page load")

    for line in [
        "Loaded 6 targets.",
        "Using User-Agent: Mozilla/5.0 (X11; Linux x86_64) Chrome/124.0.0.0",
        "Visiting https://www.youtube.com/watch?v=dQw4w9WgXcQ (dwell=8s, jitter=+0s)",
        "YouTube: consent accepted",
        "YouTube: skipped ad",
        "YouTube: length ~ 213s",
        "YouTube: progress wall=78/213s player=78/213s",
        "Visiting https://news.ycombinator.com (dwell=12s, jitter=+4s)",
        "WARN: load attempt 1/3 failed for https://blog.python.org: TimeoutException",
        "Worker: rebuilding browser after fatal session error",
    ]:
        st.add_log(f"[12:34:5{len(line) % 10}] {line}")
    return st


def main() -> None:
    docs = ROOT / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    # Width must fit the fixed columns (110) + per-column padding + borders.
    console = Console(record=True, width=134, file=open("/dev/null", "w"))
    console.print(_render(build_mock_state()))

    svg = console.export_svg(title="trafficgen --tui")
    png_path = docs / "tui-dashboard.png"
    try:
        import cairosvg

        cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=str(png_path),
                         output_width=1480)
        print(f"wrote {png_path}")
    except Exception as e:  # pragma: no cover - tooling convenience
        fallback = docs / "tui-dashboard.svg"
        fallback.write_text(svg, encoding="utf-8")
        print(f"cairosvg unavailable ({e.__class__.__name__}); wrote {fallback} instead. "
              f"Install cairosvg to produce the PNG.")


if __name__ == "__main__":
    main()
