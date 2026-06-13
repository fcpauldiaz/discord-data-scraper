"""
Send notifications to configured webhook URLs. Non-blocking; uses daemon threads.
"""
import ipaddress
import json
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from notification_watcher import format_delivered_date, to_unix_timestamp
from notification_watcher.config import get_app_logger, load_config
from notification_watcher.types import AppConfig, WebhookFormat

REQUEST_TIMEOUT = 10
RETRY_DELAYS = (1.0, 3.0, 9.0)
DISCORD_WEBHOOK_RE = re.compile(r"^https://(?:ptb\.|canary\.)?discord(?:app)?\.com/api/webhooks/", re.I)

_last_webhook_status: str = "No webhooks sent yet"
_last_webhook_time: float | None = None


def get_last_webhook_status() -> tuple[str, float | None]:
    return _last_webhook_status, _last_webhook_time


def _set_last_webhook_status(status: str) -> None:
    global _last_webhook_status, _last_webhook_time
    _last_webhook_status = status
    _last_webhook_time = time.time()


def get_webhook_config_path():
    from notification_watcher.config import get_config_path

    return get_config_path()


def validate_webhook_url(url: str) -> str | None:
    stripped = url.strip()
    if not stripped.startswith("https://"):
        return "URL must use HTTPS"
    parsed = urllib.parse.urlparse(stripped)
    if parsed.scheme != "https" or not parsed.netloc:
        return "Invalid URL"
    host = parsed.hostname
    if not host:
        return "Invalid URL host"
    if host.lower() in ("localhost",):
        return "Localhost URLs are not allowed"
    try:
        addr = ipaddress.ip_address(host)
        if addr.is_private or addr.is_loopback or addr.is_link_local:
            return "Private or local network URLs are not allowed"
    except ValueError:
        pass
    return None


def is_discord_webhook_url(url: str) -> bool:
    return bool(DISCORD_WEBHOOK_RE.match(url.strip()))


def resolve_webhook_format(url: str, config_format: WebhookFormat) -> WebhookFormat:
    if config_format == "auto":
        return "discord" if is_discord_webhook_url(url) else "generic"
    return config_format


def _platform_name() -> str:
    if sys.platform == "darwin":
        return "macos"
    if sys.platform == "win32":
        return "windows"
    return "unknown"


def build_generic_payload(
    app_id: str,
    title: str,
    subtitle: str,
    body: str,
    delivered_date: float | None,
) -> dict:
    unix_ts = to_unix_timestamp(delivered_date)
    return {
        "app_id": app_id,
        "title": title,
        "subtitle": subtitle,
        "body": body,
        "delivered_date": unix_ts,
        "delivered_date_iso": format_delivered_date(delivered_date),
        "platform": _platform_name(),
    }


def build_discord_payload(
    app_id: str,
    title: str,
    subtitle: str,
    body: str,
    delivered_date: float | None,
) -> dict:
    description_parts = [p for p in (subtitle, body) if p]
    description = "\n\n".join(description_parts) if description_parts else "(no content)"
    embed: dict = {
        "title": title or "(no title)",
        "description": description[:4096],
        "footer": {"text": app_id or "unknown"},
    }
    unix_ts = to_unix_timestamp(delivered_date)
    if unix_ts is not None:
        embed["timestamp"] = datetime.fromtimestamp(unix_ts, tz=timezone.utc).isoformat()
    return {"embeds": [embed]}


def build_payload(
    url: str,
    app_id: str,
    title: str,
    subtitle: str,
    body: str,
    delivered_date: float | None,
    config_format: WebhookFormat,
) -> tuple[bytes, str]:
    fmt = resolve_webhook_format(url, config_format)
    if fmt == "discord":
        payload = build_discord_payload(app_id, title, subtitle, body, delivered_date)
    else:
        payload = build_generic_payload(app_id, title, subtitle, body, delivered_date)
    payload_json = json.dumps(payload, ensure_ascii=False)
    return json.dumps(payload).encode("utf-8"), payload_json


def _post_one(url: str, payload_bytes: bytes, payload_json: str) -> bool:
    logger = get_app_logger()
    logger.info("Payload: %s", payload_json)
    for h in logger.handlers:
        h.flush()
    req = urllib.request.Request(
        url,
        data=payload_bytes,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    for attempt, delay in enumerate((0.0, *RETRY_DELAYS)):
        if delay:
            time.sleep(delay)
        try:
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                status = getattr(resp, "status", None)
                body = resp.read().decode("utf-8", errors="replace")
                body_preview = body[:500] + "..." if len(body) > 500 else body
                logger.info(
                    "Webhook sent to %s | status=%s | response: %s",
                    url[:50],
                    status,
                    body_preview or "(empty)",
                )
                _set_last_webhook_status(f"OK ({status})")
                return True
        except urllib.error.HTTPError as e:
            try:
                response_body = e.read().decode("utf-8", errors="replace")
            except Exception:
                response_body = ""
            body_preview = (
                response_body[:500] + "..."
                if len(response_body) > 500
                else response_body or "(empty)"
            )
            logger.warning(
                "Webhook failed %s | status=%s | response: %s (attempt %d)",
                url[:50],
                e.code,
                body_preview,
                attempt + 1,
            )
            if attempt >= len(RETRY_DELAYS):
                _set_last_webhook_status(f"Failed HTTP {e.code}")
                return False
        except (urllib.error.URLError, OSError, TimeoutError) as e:
            logger.warning("Webhook failed %s: %s (attempt %d)", url[:50], e, attempt + 1)
            if attempt >= len(RETRY_DELAYS):
                _set_last_webhook_status(f"Failed: {e}")
                return False
    return False


def _should_forward(app_id: str, config: AppConfig) -> bool:
    if not config.webhook_discord_only:
        return True
    return "discord" in app_id.lower()


def send_notification_webhook(
    app_id: str,
    title: str,
    subtitle: str,
    body: str,
    delivered_date: float | None,
    config: AppConfig | None = None,
) -> None:
    cfg = config or load_config()
    if not _should_forward(app_id, cfg):
        return
    urls = cfg.webhook_urls
    if not urls:
        get_app_logger().info("Notification skipped: no webhooks configured")
        return
    get_app_logger().info(
        "Notification: %s | %s",
        title or "(no title)",
        body[:80] + "..." if len(body) > 80 else body,
    )

    def run_for_url(target_url: str) -> None:
        payload_bytes, payload_json = build_payload(
            target_url, app_id, title, subtitle, body, delivered_date, cfg.webhook_format
        )
        _post_one(target_url.strip(), payload_bytes, payload_json)

    for webhook_url in urls:
        threading.Thread(target=run_for_url, args=(webhook_url,), daemon=True).start()


def send_discord_notification(
    app_id: str,
    title: str,
    subtitle: str,
    body: str,
    delivered_date: float | None,
) -> None:
    send_notification_webhook(app_id, title, subtitle, body, delivered_date)


def send_test_webhook() -> tuple[bool, str]:
    config = load_config()
    if not config.webhook_urls:
        return False, "No webhooks configured"
    url = config.webhook_urls[0]
    error = validate_webhook_url(url)
    if error:
        return False, error
    payload_bytes, payload_json = build_payload(
        url,
        "com.notificationwatcher.test",
        "Test notification",
        "Webhook test",
        "If you see this, webhooks are working.",
        None,
        config.webhook_format,
    )
    ok = _post_one(url.strip(), payload_bytes, payload_json)
    return ok, "Test webhook sent" if ok else get_last_webhook_status()[0]


def load_webhook_urls() -> list[str]:
    from notification_watcher.config import load_webhook_urls as _load

    return _load()


def save_webhook_urls(urls: list[str]) -> None:
    from notification_watcher.config import save_webhook_urls as _save

    _save(urls)
