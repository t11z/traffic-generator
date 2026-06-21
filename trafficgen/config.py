"""Configuration model and loading. No Selenium import — fully testable."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .actions import Action, build_action

try:  # optional dependency, mirrors the original lazy import
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None


DEFAULT_WINDOW_SIZE = "1280,800"
DEFAULT_PAGE_LOAD_TIMEOUT = 60


@dataclass
class Target:
    url: str
    interval_seconds: int
    dwell_seconds: int
    jitter_seconds: int = 0
    scroll: bool = True
    handler: Optional[str] = None
    actions: List[Action] = field(default_factory=list)
    next_run: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @staticmethod
    def from_dict(d: Dict[str, Any], defaults: Dict[str, Any]) -> "Target":
        def get(name: str, fallback: Any) -> Any:
            return d.get(name, defaults.get(name, fallback))

        url = d.get("url")
        if not url or not isinstance(url, str):
            raise ValueError("Each target requires a valid 'url' string")
        interval = int(get("interval_seconds", 300))
        dwell = int(get("dwell_seconds", 8))
        jitter = int(get("jitter_seconds", 0))
        scroll = bool(get("scroll", True))
        handler = d.get("handler") or defaults.get("handler")
        handler = str(handler) if handler else None

        raw_actions = d.get("actions")
        if raw_actions is None:
            raw_actions = defaults.get("actions")
        actions: List[Action] = []
        if raw_actions:
            if not isinstance(raw_actions, list):
                raise ValueError(f"'actions' for {url} must be a list")
            actions = [build_action(a) for a in raw_actions]

        return Target(
            url=url,
            interval_seconds=interval,
            dwell_seconds=dwell,
            jitter_seconds=jitter,
            scroll=scroll,
            handler=handler,
            actions=actions,
        )


@dataclass
class Settings:
    """Runtime knobs resolved from CLI flags and config ``defaults``."""

    headless: bool = True
    ignore_cert_errors: bool = False
    yt_wallclock: bool = False
    page_load_timeout: int = DEFAULT_PAGE_LOAD_TIMEOUT
    window_size: str = DEFAULT_WINDOW_SIZE
    max_retries: int = 3
    retry_backoff: float = 2.0


@dataclass
class Config:
    targets: List[Target]
    user_agents: List[str]
    raw_defaults: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def load(path: Optional[Path]) -> "Config":
        if path is None:
            return Config(
                targets=[Target(url="https://example.com", interval_seconds=300, dwell_seconds=8)],
                user_agents=[],
            )

        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        raw: Dict[str, Any]
        if path.suffix.lower() in {".yaml", ".yml"}:
            if yaml is None:
                raise RuntimeError("PyYAML not installed; install with 'pip install pyyaml'")
            with path.open("r", encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}
        else:
            with path.open("r", encoding="utf-8") as f:
                raw = json.load(f)

        defaults = raw.get("defaults", {}) or {}
        user_agents = list(raw.get("user_agents", []) or [])
        targets_raw = raw.get("targets", [])
        if not isinstance(targets_raw, list) or not targets_raw:
            raise ValueError("Config must include a non-empty 'targets' list")

        targets = [Target.from_dict(t, defaults) for t in targets_raw]
        return Config(targets=targets, user_agents=user_agents, raw_defaults=defaults)

    def apply_defaults_to_settings(self, settings: Settings) -> Settings:
        """Fill unset Settings fields from the config ``defaults`` block.

        CLI flags win: the caller passes a Settings already populated from the
        command line; here we only fill values the config provides and the CLI
        left at the dataclass default.
        """
        d = self.raw_defaults
        if "page_load_timeout" in d and settings.page_load_timeout == DEFAULT_PAGE_LOAD_TIMEOUT:
            settings.page_load_timeout = int(d["page_load_timeout"])
        if "window_size" in d and settings.window_size == DEFAULT_WINDOW_SIZE:
            settings.window_size = str(d["window_size"]).replace("x", ",")
        if "max_retries" in d and settings.max_retries == 3:
            settings.max_retries = int(d["max_retries"])
        if "retry_backoff" in d and settings.retry_backoff == 2.0:
            settings.retry_backoff = float(d["retry_backoff"])
        return settings
