"""Logging helper with a swappable output sink.

By default :func:`log` prints to stdout exactly like the original script. In TUI
mode the sink is replaced so log lines are appended to a ring buffer instead of
corrupting the live display. An optional file sink can tee lines to a log file.
"""
from __future__ import annotations

from datetime import datetime
from typing import Callable, List, Optional

# The active sink receives the fully formatted line (already timestamped).
_sink: Optional[Callable[[str], None]] = None
_file_sink: Optional[Callable[[str], None]] = None


def _format(msg: str) -> str:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"[{ts}] {msg}"


def set_sink(sink: Optional[Callable[[str], None]]) -> None:
    """Install the primary sink. ``None`` restores stdout printing."""
    global _sink
    _sink = sink


def set_file_sink(sink: Optional[Callable[[str], None]]) -> None:
    """Install an additional sink (e.g. a log file). Receives the same line."""
    global _file_sink
    _file_sink = sink


def log(msg: str) -> None:
    line = _format(msg)
    if _sink is not None:
        _sink(line)
    else:
        print(line, flush=True)
    if _file_sink is not None:
        try:
            _file_sink(line)
        except Exception:
            pass


def make_file_sink(path) -> Callable[[str], None]:
    """Return a sink that appends lines to ``path`` (best effort)."""
    def _write(line: str) -> None:
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass
    return _write
