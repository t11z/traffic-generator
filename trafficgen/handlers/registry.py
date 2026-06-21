"""Handler registry: match a URL to a handler, with priority and fallback."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from .base import Handler

_Matcher = Callable[[str], bool]


@dataclass
class _Entry:
    name: str
    matcher: _Matcher
    handler: Handler
    priority: int


_ENTRIES: List[_Entry] = []
_BY_NAME: Dict[str, Handler] = {}
_DEFAULT: Optional[Handler] = None


def register_handler(name: str, matcher: _Matcher, handler: Handler, priority: int = 0) -> None:
    _ENTRIES.append(_Entry(name, matcher, handler, priority))
    _ENTRIES.sort(key=lambda e: e.priority, reverse=True)
    _BY_NAME[name] = handler


def set_default_handler(handler: Handler) -> None:
    global _DEFAULT
    _DEFAULT = handler
    _BY_NAME["default"] = handler


def dispatch(url: str, explicit_name: Optional[str] = None) -> Handler:
    """Return the handler for ``url``.

    Priority: explicit ``handler:`` name > first matching matcher > default.
    """
    if explicit_name:
        h = _BY_NAME.get(explicit_name)
        if h is None:
            raise ValueError(
                f"Unknown handler {explicit_name!r}. Known: {', '.join(sorted(_BY_NAME))}"
            )
        return h
    for entry in _ENTRIES:
        try:
            if entry.matcher(url):
                return entry.handler
        except Exception:
            continue
    if _DEFAULT is None:  # pragma: no cover - default always registered
        raise RuntimeError("No default handler registered")
    return _DEFAULT


def known_handlers() -> List[str]:
    return sorted(_BY_NAME)
