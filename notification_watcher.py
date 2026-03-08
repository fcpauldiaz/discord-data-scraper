"""
Core logic for reading macOS Notification Center SQLite database.
No GUI or argparse; used by scraper CLI and menu bar app.
"""
import plistlib
import sqlite3
import subprocess
import time
from pathlib import Path
from typing import Callable, Iterator

DeliveredDate = float | None
Notification = tuple[str, str, str, str, int | None, DeliveredDate]
OnNotification = Callable[[str, str, str, str, DeliveredDate], None]

MAC_EPOCH_OFFSET = 978307200


def _notification_db_candidates() -> Iterator[Path]:
    home = Path.home()
    yield home / "Library" / "Group Containers" / "group.com.apple.usernoted" / "db2" / "db"
    result = subprocess.run(
        ["getconf", "DARWIN_USER_DIR"],
        capture_output=True,
        text=True,
        timeout=5,
    )
    if result.returncode == 0 and result.stdout.strip():
        base = Path(result.stdout.strip())
        yield base / "com.apple.notificationcenter" / "db2" / "db"
        yield base / "com.apple.notificationcenter" / "db" / "db"
    yield home / "Library" / "Application Support" / "NotificationCenter" / "db2" / "db"
    yield home / "Library" / "Application Support" / "NotificationCenter" / "db" / "db"
    yield home / "Library" / "Group Containers" / "group.com.apple.UserNotifications" / "Library" / "UserNotifications" / "db2" / "db"


def get_notification_db_path() -> Path | None:
    for candidate in _notification_db_candidates():
        if candidate.exists():
            return candidate
    first = next(_notification_db_candidates(), None)
    return first


def _to_str(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, list):
        return " ".join(_to_str(x) for x in value)
    return str(value)


def parse_notification_plist(data: bytes) -> dict[str, str]:
    out: dict[str, str] = {"title": "", "subtitle": "", "body": ""}
    try:
        plist = plistlib.loads(data)
    except (plistlib.InvalidFileException, ValueError):
        return out
    req = plist.get("req") if isinstance(plist, dict) else None
    if not isinstance(req, dict):
        return out
    out["title"] = _to_str(req.get("titl") or req.get("title"))
    out["subtitle"] = _to_str(req.get("subt") or req.get("subtitle"))
    out["body"] = _to_str(req.get("body") or req.get("message"))
    return out


def format_delivered_date(mac_abs_seconds: DeliveredDate) -> str:
    if mac_abs_seconds is None or mac_abs_seconds <= 0:
        return ""
    from datetime import datetime

    unix_ts = mac_abs_seconds + MAC_EPOCH_OFFSET
    return datetime.utcfromtimestamp(unix_ts).strftime("%Y-%m-%d %H:%M:%S UTC")


def iter_notifications(db_path: Path, app_filter: str | None = None) -> Iterator[Notification]:
    if not db_path.exists():
        raise FileNotFoundError(
            f"Notification Center database not found at {db_path}. "
            "On macOS Tahoe (26) and Sequoia (15) the DB may be in a protected location. "
            "Grant Full Disk Access to Terminal (or this app) in System Settings > Privacy & Security, "
            "or pass the DB path with --db if you know it."
        )
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        sql = """
            SELECT
                (SELECT identifier FROM app WHERE app.app_id = record.app_id) AS app_id,
                record.rec_id,
                record.data,
                record.delivered_date,
                record.presented
            FROM record
        """
        params: tuple = ()
        if app_filter is not None:
            sql += " WHERE LOWER((SELECT identifier FROM app WHERE app.app_id = record.app_id)) LIKE ?"
            params = (app_filter.lower(),)
        sql += " ORDER BY record.delivered_date DESC"
        cursor = conn.execute(sql, params)
        for row in cursor:
            app_id = row["app_id"] or ""
            parsed = parse_notification_plist(row["data"])
            yield (
                app_id,
                parsed["title"],
                parsed["subtitle"],
                parsed["body"],
                row["presented"],
                row["delivered_date"],
            )
    finally:
        conn.close()


def watch(
    db_path: Path,
    poll_seconds: float,
    app_filter: str | None,
    on_notification: OnNotification,
    stop_flag: Callable[[], bool] | None = None,
) -> None:
    seen: set[tuple[str, str, str, str, DeliveredDate]] = set()
    while True:
        if stop_flag and stop_flag():
            return
        try:
            for app_id, title, subtitle, body, _presented, delivered_date in iter_notifications(
                db_path, app_filter
            ):
                if stop_flag and stop_flag():
                    return
                key = (app_id, title, subtitle, body, delivered_date)
                if key not in seen:
                    seen.add(key)
                    on_notification(app_id, title, subtitle, body, delivered_date)
        except FileNotFoundError:
            pass
        time.sleep(poll_seconds)
