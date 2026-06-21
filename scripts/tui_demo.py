#!/usr/bin/env python3
"""Render the TUI dashboard with mock data to a PNG "screenshot".

Used to generate docs/tui-dashboard.png for the README. Regenerate with::

    python3 scripts/tui_demo.py

The dashboard is drawn character-by-character onto a fixed monospace grid with
Pillow. This deliberately bypasses rich's SVG export (which embeds an external
web font and uses ``textLength``, causing box-drawing characters to drift on
GitHub). Drawing each cell at ``col * char_width`` with a real monospace font
keeps every border perfectly aligned. Requires Pillow (dev/doc tooling only).
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

RENDER_WIDTH = 134
FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
FONT_SIZE = 20
BG = (12, 12, 16)
DEFAULT_FG = (200, 200, 200)


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


def _fg(style) -> tuple:
    try:
        if style is not None and style.color is not None:
            t = style.color.get_truecolor()
            return (t.red, t.green, t.blue)
    except Exception:
        pass
    return DEFAULT_FG


def _bg(style):
    try:
        if style is not None and style.bgcolor is not None:
            t = style.bgcolor.get_truecolor()
            return (t.red, t.green, t.blue)
    except Exception:
        pass
    return None


def main() -> None:
    from PIL import Image, ImageDraw, ImageFont

    docs = ROOT / "docs"
    docs.mkdir(parents=True, exist_ok=True)

    console = Console(width=RENDER_WIDTH, file=open("/dev/null", "w"))
    options = console.options.update(width=RENDER_WIDTH)
    lines = console.render_lines(_render(build_mock_state()), options, pad=True)

    font = ImageFont.truetype(FONT_REGULAR, FONT_SIZE)
    font_bold = ImageFont.truetype(FONT_BOLD, FONT_SIZE)
    # Monospace cell metrics from the font itself.
    cell_w = font.getlength("M")
    ascent, descent = font.getmetrics()
    line_h = ascent + descent + 2

    margin = 16
    img_w = int(round(cell_w * RENDER_WIDTH)) + 2 * margin
    img_h = line_h * len(lines) + 2 * margin
    img = Image.new("RGB", (img_w, img_h), BG)
    draw = ImageDraw.Draw(img)

    for row, segments in enumerate(lines):
        col = 0
        y = margin + row * line_h
        for seg in segments:
            text = seg.text
            if not text:
                continue
            fg = _fg(seg.style)
            bg = _bg(seg.style)
            bold = bool(seg.style and seg.style.bold)
            f = font_bold if bold else font
            for ch in text:
                x = margin + int(round(col * cell_w))
                if bg is not None:
                    draw.rectangle([x, y, x + int(round(cell_w)), y + line_h], fill=bg)
                if ch != " ":
                    draw.text((x, y), ch, font=f, fill=fg)
                col += 1

    out = docs / "tui-dashboard.png"
    img.save(out)
    print(f"wrote {out} ({img_w}x{img_h})")


if __name__ == "__main__":
    main()
