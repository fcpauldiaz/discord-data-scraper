import sqlite3
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

from notification_watcher.types import DeliveredDate, Notification

WINDOWS_FILETIME_OFFSET = 11644473600
WINDOWS_FILETIME_SCALE = 10_000_000
PLATFORM_NAME = "windows"


def get_notification_db_path() -> Path | None:
    local_app_data = Path.home() / "AppData" / "Local"
    candidate = local_app_data / "Microsoft" / "Windows" / "Notifications" / "wpndatabase.db"
    if candidate.exists():
        return candidate
    return candidate


def _decode_payload(raw: object) -> str:
    if raw is None:
        return ""
    if isinstance(raw, str):
        return raw
    if isinstance(raw, bytes):
        for encoding in ("utf-8", "utf-16-le", "utf-16"):
            try:
                return raw.decode(encoding)
            except UnicodeDecodeError:
                continue
        return raw.decode("utf-8", errors="replace")
    return str(raw)


def parse_notification_xml(payload: str) -> dict[str, str]:
    out: dict[str, str] = {"title": "", "subtitle": "", "body": ""}
    if not payload.strip():
        return out
    try:
        root = ET.fromstring(payload)
    except ET.ParseError:
        return out

    texts: list[str] = []
    for elem in root.iter():
        tag = elem.tag.split("}")[-1].lower() if "}" in elem.tag else elem.tag.lower()
        if tag == "text" and elem.text and elem.text.strip():
            texts.append(elem.text.strip())

    if texts:
        out["title"] = texts[0]
    if len(texts) > 1:
        out["subtitle"] = texts[1]
    if len(texts) > 2:
        out["body"] = " ".join(texts[2:])
    elif len(texts) == 2 and not out["body"]:
        out["body"] = texts[1]
        out["subtitle"] = ""

    return out


def to_unix_timestamp(arrival_time: DeliveredDate) -> float | None:
    if arrival_time is None or arrival_time <= 0:
        return None
    return (arrival_time / WINDOWS_FILETIME_SCALE) - WINDOWS_FILETIME_OFFSET


def format_delivered_date(delivered_date: DeliveredDate) -> str:
    unix_ts = to_unix_timestamp(delivered_date)
    if unix_ts is None:
        return ""
    return datetime.utcfromtimestamp(unix_ts).strftime("%Y-%m-%d %H:%M:%S UTC")


def iter_notifications(
    db_path: Path,
    app_filter: str | None = None,
    since_date: DeliveredDate = None,
) -> Iterator[Notification]:
    if not db_path.exists():
        raise FileNotFoundError(
            f"Windows notification database not found at {db_path}. "
            "Ensure Action Center notifications are enabled and the database exists."
        )
    uri = f"file:{db_path.as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    try:
        sql = """
            SELECT
                nh.PrimaryId AS app_id,
                n.Payload AS data,
                n.ArrivalTime AS delivered_date
            FROM Notification n
            INNER JOIN NotificationHandler nh ON n.HandlerId = nh.RecordId
            WHERE 1=1
        """
        params: list[object] = []
        if app_filter is not None:
            sql += " AND LOWER(nh.PrimaryId) LIKE ?"
            params.append(app_filter.lower())
        if since_date is not None and since_date > 0:
            sql += " AND n.ArrivalTime > ?"
            params.append(since_date)
        sql += " ORDER BY n.ArrivalTime DESC"
        cursor = conn.execute(sql, tuple(params))
        for row in cursor:
            app_id = row["app_id"] or ""
            parsed = parse_notification_xml(_decode_payload(row["data"]))
            yield (
                app_id,
                parsed["title"],
                parsed["subtitle"],
                parsed["body"],
                None,
                row["delivered_date"],
            )
    finally:
        conn.close()
