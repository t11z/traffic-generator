"""Registry mapping an action ``type`` string to a factory."""
from __future__ import annotations

from typing import Callable, Dict, List

from .base import Action

_FACTORIES: Dict[str, Callable[[dict], Action]] = {}


def register_action(type_name: str, factory: Callable[[dict], Action]) -> None:
    _FACTORIES[type_name] = factory


def valid_action_types() -> List[str]:
    return sorted(_FACTORIES)


def build_action(d: dict) -> Action:
    if not isinstance(d, dict):
        raise ValueError(f"Action must be a mapping, got {type(d).__name__}")
    type_name = d.get("type")
    if not type_name:
        raise ValueError("Each action requires a 'type' key")
    factory = _FACTORIES.get(type_name)
    if factory is None:
        raise ValueError(
            f"Unknown action type {type_name!r}. "
            f"Valid types: {', '.join(valid_action_types()) or '(none)'}"
        )
    return factory(d)
