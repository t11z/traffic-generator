"""Per-target action registry and built-ins."""
from __future__ import annotations

from .base import Action, ActionContext
from .registry import build_action, register_action, valid_action_types

# Importing builtins registers the built-in action types as a side effect.
from . import builtins as _builtins  # noqa: F401

__all__ = [
    "Action",
    "ActionContext",
    "build_action",
    "register_action",
    "valid_action_types",
]
