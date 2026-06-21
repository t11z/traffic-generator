import json
from pathlib import Path

import pytest

from trafficgen.config import Config, Settings, Target

FIXTURES = Path(__file__).resolve().parent / "fixtures"
REPO_ROOT = Path(__file__).resolve().parent.parent


def test_target_from_dict_full():
    t = Target.from_dict(
        {"url": "https://x.test", "interval_seconds": 100, "dwell_seconds": 7,
         "jitter_seconds": 3, "scroll": False},
        defaults={},
    )
    assert t.url == "https://x.test"
    assert t.interval_seconds == 100
    assert t.dwell_seconds == 7
    assert t.jitter_seconds == 3
    assert t.scroll is False
    assert t.actions == []
    assert t.handler is None


def test_target_defaults_three_level_merge():
    defaults = {"interval_seconds": 200, "dwell_seconds": 9, "scroll": True}
    # target overrides defaults; defaults override hardcoded fallback
    t = Target.from_dict({"url": "https://x.test", "dwell_seconds": 4}, defaults)
    assert t.dwell_seconds == 4          # from target
    assert t.interval_seconds == 200     # from defaults
    assert t.jitter_seconds == 0         # hardcoded fallback


def test_target_missing_url_raises():
    with pytest.raises(ValueError):
        Target.from_dict({"interval_seconds": 100}, {})
    with pytest.raises(ValueError):
        Target.from_dict({"url": 123}, {})


def test_config_load_yaml(monkeypatch):
    cfg = Config.load(FIXTURES / "full.yaml")
    assert len(cfg.targets) == 4
    assert cfg.user_agents
    hn = {t.url: t for t in cfg.targets}
    assert len(hn["https://news.ycombinator.com"].actions) == 3
    assert hn["https://example.org/feed"].handler == "infinite_scroll"


def test_config_load_json():
    cfg = Config.load(FIXTURES / "minimal.json")
    assert len(cfg.targets) == 1
    assert cfg.targets[0].interval_seconds == 60


def test_config_load_missing_file():
    with pytest.raises(FileNotFoundError):
        Config.load(Path("/nonexistent/file.yaml"))


def test_config_empty_targets(tmp_path):
    p = tmp_path / "empty.json"
    p.write_text(json.dumps({"targets": []}))
    with pytest.raises(ValueError):
        Config.load(p)


def test_unknown_action_type(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({"targets": [
        {"url": "https://x.test", "actions": [{"type": "does_not_exist"}]}
    ]}))
    with pytest.raises(ValueError) as exc:
        Config.load(p)
    assert "does_not_exist" in str(exc.value)


def test_legacy_urls_yaml_still_loads():
    """The repo's shipped urls.yaml must keep loading with no actions."""
    cfg = Config.load(REPO_ROOT / "urls.yaml")
    assert cfg.targets
    # legacy targets have no actions configured
    assert all(isinstance(t.actions, list) for t in cfg.targets)


def test_apply_defaults_to_settings():
    cfg = Config.load(FIXTURES / "full.yaml")
    s = Settings()  # CLI left at defaults
    cfg.apply_defaults_to_settings(s)
    assert s.page_load_timeout == 45
    assert s.window_size == "1600,900"
    assert s.max_retries == 5


def test_apply_defaults_does_not_override_cli():
    cfg = Config.load(FIXTURES / "full.yaml")
    s = Settings(page_load_timeout=15, max_retries=2)  # CLI-provided
    cfg.apply_defaults_to_settings(s)
    assert s.page_load_timeout == 15  # CLI wins
    assert s.max_retries == 2
