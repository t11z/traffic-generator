"""Rich-based live dashboard. Imported lazily so plain mode never needs rich."""
from __future__ import annotations

import threading
import time
from datetime import datetime
from typing import Optional

from .state import RunState, Status


def rich_available() -> bool:
    try:
        import rich  # noqa: F401
        return True
    except Exception:
        return False


_STATUS_STYLE = {
    Status.IDLE: "dim",
    Status.LOADING: "yellow",
    Status.WATCHING: "cyan",
    Status.SCROLLING: "cyan",
    Status.ACTING: "magenta",
    Status.WAITING: "green",
    Status.ERROR: "bold red",
}


def _fmt_next_run(dt: Optional[datetime]) -> str:
    if dt is None:
        return "-"
    try:
        return dt.astimezone().strftime("%H:%M:%S")
    except Exception:
        return "-"


def _fmt_progress(frac: Optional[float]) -> str:
    if frac is None:
        return ""
    blocks = int(round(frac * 10))
    return f"{'█' * blocks}{'░' * (10 - blocks)} {int(frac * 100):3d}%"


def _render(state: RunState):
    from rich.console import Group
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    meta = state.snapshot_meta()
    table = Table(expand=True)
    table.add_column("Target", overflow="fold", ratio=3)
    table.add_column("Status", ratio=1)
    table.add_column("Activity", ratio=2)
    table.add_column("Progress", ratio=2)
    table.add_column("Next", justify="right", ratio=1)
    table.add_column("Visits", justify="right", ratio=1)
    table.add_column("Err", justify="right", ratio=1)

    for ts in state.snapshot_targets():
        style = _STATUS_STYLE.get(ts.status, "white")
        table.add_row(
            ts.url,
            Text(ts.status, style=style),
            ts.activity or "",
            _fmt_progress(ts.progress),
            _fmt_next_run(ts.next_run),
            str(ts.visits),
            str(ts.errors),
        )

    log_lines = state.snapshot_log()[-12:]
    log_panel = Panel(
        Text("\n".join(log_lines) or "(no log yet)", no_wrap=False),
        title="Log",
        border_style="dim",
    )
    ua = (meta.get("user_agent") or "default")
    header = Text(
        f"Traffic Generator  ·  UA: {ua[:60]}  ·  rebuilds: {meta['driver_rebuilds']}",
        style="bold",
    )
    return Group(header, table, log_panel)


def run_dashboard(state: RunState, stop_event: threading.Event, worker_thread: threading.Thread,
                  refresh_per_second: float = 4.0) -> None:
    """Render the dashboard on the main thread until the worker stops."""
    from rich.live import Live

    with Live(_render(state), refresh_per_second=refresh_per_second, screen=False) as live:
        while worker_thread.is_alive() and not stop_event.is_set():
            live.update(_render(state))
            time.sleep(1.0 / refresh_per_second)
        live.update(_render(state))
