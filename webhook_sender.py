"""
Send Discord notifications to configured webhook URLs. Non-blocking; uses daemon thread.
"""
import json
import logging
import threading
import urllib.error
import urllib.request
from pathlib import Path

from notification_watcher import format_delivered_date

CONFIG_DIR_NAME = "Notification Watcher"
CONFIG_FILENAME = "config.json"
LOG_FILENAME = "notification_watcher.log"
WEBHOOK_URLS_KEY = "webhook_urls"
REQUEST_TIMEOUT = 10

_APP_LOGGER: logging.Logger | None = None


def get_webhook_config_path() -> Path:
    return Path.home() / "Library" / "Application Support" / CONFIG_DIR_NAME / CONFIG_FILENAME


def get_app_logger() -> logging.Logger:
    global _APP_LOGGER
    if _APP_LOGGER is not None:
        return _APP_LOGGER
    log_path = get_webhook_config_path().parent / LOG_FILENAME
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("notification_watcher")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        fh = logging.FileHandler(log_path, encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(fh)
    _APP_LOGGER = logger
    return logger


def load_webhook_urls() -> list[str]:
    path = get_webhook_config_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    urls = data.get(WEBHOOK_URLS_KEY)
    if not isinstance(urls, list):
        return []
    return [u for u in urls if isinstance(u, str) and u.strip()]


def save_webhook_urls(urls: list[str]) -> None:
    path = get_webhook_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({WEBHOOK_URLS_KEY: urls}, indent=2),
        encoding="utf-8",
    )


def _post_one(url: str, payload: bytes) -> None:
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT)
        get_app_logger().info("Webhook sent to %s", url[:60] + "..." if len(url) > 60 else url)
    except (urllib.error.URLError, OSError, TimeoutError) as e:
        get_app_logger().warning("Webhook failed %s: %s", url[:50], e)


def send_discord_notification(
    app_id: str,
    title: str,
    subtitle: str,
    body: str,
    delivered_date: float | None,
) -> None:
    if "discord" not in app_id.lower():
        return
    urls = load_webhook_urls()
    if not urls:
        get_app_logger().info("Discord notification skipped: no webhooks configured")
        return
    get_app_logger().info("Discord notification: %s | %s", title or "(no title)", body[:80] + "..." if len(body) > 80 else body)
    unix_ts = None
    if delivered_date is not None and delivered_date > 0:
        unix_ts = delivered_date + 978307200
    payload = {
        "app_id": app_id,
        "title": title,
        "subtitle": subtitle,
        "body": body,
        "delivered_date": unix_ts,
        "delivered_date_iso": format_delivered_date(delivered_date),
    }
    payload_bytes = json.dumps(payload).encode("utf-8")
    for url in urls:
        t = threading.Thread(target=_post_one, args=(url.strip(), payload_bytes), daemon=True)
        t.start()
