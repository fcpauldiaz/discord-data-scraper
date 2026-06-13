import json
import logging
import os
import sys
from pathlib import Path

from notification_watcher.types import AppConfig, WebhookFormat

CONFIG_DIR_NAME = "Notification Watcher"
CONFIG_FILENAME = "config.json"
LOG_FILENAME = "notification_watcher.log"

_APP_LOGGER: logging.Logger | None = None


def get_config_dir() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / CONFIG_DIR_NAME
    return Path(os.environ.get("APPDATA", Path.home())) / CONFIG_DIR_NAME


def get_config_path() -> Path:
    return get_config_dir() / CONFIG_FILENAME


def get_log_path() -> Path:
    return get_config_dir() / LOG_FILENAME


def get_app_logger() -> logging.Logger:
    global _APP_LOGGER
    if _APP_LOGGER is not None:
        return _APP_LOGGER
    log_path = get_log_path()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("notification_watcher")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        fh = logging.FileHandler(log_path, encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(fh)
    _APP_LOGGER = logger
    return logger


def _parse_webhook_format(value: object) -> WebhookFormat:
    if value in ("auto", "discord", "generic"):
        return value
    return "auto"


def default_config() -> AppConfig:
    return AppConfig()


def load_config() -> AppConfig:
    path = get_config_path()
    if not path.exists():
        return default_config()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default_config()
    if not isinstance(data, dict):
        return default_config()
    urls = data.get("webhook_urls")
    webhook_urls = (
        [u.strip() for u in urls if isinstance(u, str) and u.strip()]
        if isinstance(urls, list)
        else []
    )
    poll = data.get("poll_seconds")
    poll_seconds = float(poll) if isinstance(poll, (int, float)) and poll > 0 else 0.5
    app_filter = data.get("app_filter")
    return AppConfig(
        webhook_urls=webhook_urls,
        poll_seconds=poll_seconds,
        discord_only=bool(data.get("discord_only", False)),
        app_filter=app_filter if isinstance(app_filter, str) and app_filter else None,
        webhook_discord_only=bool(data.get("webhook_discord_only", False)),
        launch_at_login=bool(data.get("launch_at_login", False)),
        webhook_format=_parse_webhook_format(data.get("webhook_format")),
    )


def save_config(config: AppConfig) -> None:
    path = get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "webhook_urls": config.webhook_urls,
        "poll_seconds": config.poll_seconds,
        "discord_only": config.discord_only,
        "app_filter": config.app_filter,
        "webhook_discord_only": config.webhook_discord_only,
        "launch_at_login": config.launch_at_login,
        "webhook_format": config.webhook_format,
    }
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_webhook_urls() -> list[str]:
    return load_config().webhook_urls


def save_webhook_urls(urls: list[str]) -> None:
    config = load_config()
    config.webhook_urls = urls
    save_config(config)
