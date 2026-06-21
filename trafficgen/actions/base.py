"""Action abstraction: a small, configurable step performed during a visit."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional


@dataclass
class ActionContext:
    """Everything an action needs to run.

    ``driver`` is a Selenium WebDriver (duck-typed here so this module stays
    import-light and testable). ``report_progress`` and ``log`` let actions
    surface state to the dashboard / stdout. ``stop_event`` is a
    ``threading.Event`` (or ``None``) that signals a graceful shutdown.
    """

    driver: Any
    target: Any
    log: Callable[[str], None]
    report_progress: Callable[[Optional[float], str], None] = lambda frac, text: None
    stop_event: Any = None

    def should_stop(self) -> bool:
        return bool(self.stop_event is not None and self.stop_event.is_set())


class Action:
    """Base class for actions. Subclasses implement :meth:`run`."""

    type: str = "base"

    @classmethod
    def from_dict(cls, d: dict) -> "Action":  # pragma: no cover - overridden
        raise NotImplementedError

    def run(self, ctx: ActionContext) -> None:  # pragma: no cover - overridden
        raise NotImplementedError
