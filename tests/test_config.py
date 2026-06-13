import json
from pathlib import Path

import pytest

from notification_watcher.config import default_config, load_config, save_config
from notification_watcher.types import AppConfig


def test_default_config():
    cfg = default_config()
    assert cfg.webhook_urls == []
    assert cfg.poll_seconds == 0.5
    assert cfg.webhook_format == "auto"


def test_config_round_trip(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(
        "notification_watcher.config.get_config_path",
        lambda: tmp_path / "config.json",
    )
    cfg = AppConfig(
        webhook_urls=["https://example.com/hook"],
        poll_seconds=0.1,
        discord_only=True,
        app_filter="%slack%",
        webhook_discord_only=True,
        launch_at_login=True,
        webhook_format="discord",
    )
    save_config(cfg)
    loaded = load_config()
    assert loaded.webhook_urls == ["https://example.com/hook"]
    assert loaded.poll_seconds == 0.1
    assert loaded.discord_only is True
    assert loaded.app_filter == "%slack%"
    assert loaded.webhook_discord_only is True
    assert loaded.launch_at_login is True
    assert loaded.webhook_format == "discord"


def test_effective_app_filter():
    cfg = AppConfig(discord_only=True, app_filter="%slack%")
    assert cfg.effective_app_filter() == "%discord%"
    cfg.discord_only = False
    assert cfg.effective_app_filter() == "%slack%"


def test_load_config_invalid_json(tmp_path: Path, monkeypatch):
    path = tmp_path / "config.json"
    path.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr("notification_watcher.config.get_config_path", lambda: path)
    assert load_config() == default_config()
