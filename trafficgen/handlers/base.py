"""Handler abstraction: full per-visit behaviour selected by URL or config."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional


@dataclass
class HandlerContext:
    driver: Any
    target: Any            # config.Target
    settings: Any          # config.Settings
    log: Callable[[str], None]
    report_progress: Callable[[Optional[float], str], None] = lambda frac, text: None
    stop_event: Any = None

    def should_stop(self) -> bool:
        return bool(self.stop_event is not None and self.stop_event.is_set())


# A handler takes a HandlerContext and drives the whole visit.
Handler = Callable[[HandlerContext], None]
