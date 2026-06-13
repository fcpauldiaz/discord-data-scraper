import time
from collections import OrderedDict
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from notification_watcher.types import DeliveredDate, Notification, OnError, OnNotification

SEEN_MAX = 5000
SLEEP_CHUNK = 0.01
PollValue = float | Callable[[], float]
FilterValue = str | None | Callable[[], str | None]


class NotificationBackend(Protocol):
    PLATFORM_NAME: str

    def get_notification_db_path(self) -> Path | None: ...

    def iter_notifications(
        self,
        db_path: Path,
        app_filter: str | None = None,
        since_date: DeliveredDate = None,
    ): ...


class SeenTracker:
    def __init__(self, max_size: int = SEEN_MAX) -> None:
        self._max_size = max_size
        self._keys: OrderedDict[tuple[str, str, str, str, DeliveredDate], None] = OrderedDict()

    def add(self, key: tuple[str, str, str, str, DeliveredDate]) -> bool:
        if key in self._keys:
            return False
        self._keys[key] = None
        if len(self._keys) > self._max_size:
            self._keys.popitem(last=False)
        return True


def _interruptible_sleep(seconds: float, stop_flag) -> bool:
    remaining = seconds
    while remaining > 0:
        if stop_flag and stop_flag():
            return True
        step = min(SLEEP_CHUNK, remaining)
        time.sleep(step)
        remaining -= step
    return bool(stop_flag and stop_flag())


def _max_delivered_date(notifications: list[Notification]) -> DeliveredDate:
    best: DeliveredDate = None
    for *_, delivered_date in notifications:
        if delivered_date is not None and (best is None or delivered_date > best):
            best = delivered_date
    return best


def _resolve_poll(poll_seconds: PollValue) -> float:
    return poll_seconds() if callable(poll_seconds) else poll_seconds


def _resolve_filter(app_filter: FilterValue) -> str | None:
    return app_filter() if callable(app_filter) else app_filter


def watch(
    backend: NotificationBackend,
    db_path: Path,
    poll_seconds: PollValue,
    app_filter: FilterValue,
    on_notification: OnNotification,
    stop_flag=None,
    on_error: OnError | None = None,
) -> None:
    seen = SeenTracker()
    since_date: DeliveredDate = None
    while True:
        if stop_flag and stop_flag():
            return
        resolved_filter = _resolve_filter(app_filter)
        try:
            batch = list(
                backend.iter_notifications(db_path, resolved_filter, since_date=since_date)
            )
            for app_id, title, subtitle, body, _presented, delivered_date in reversed(batch):
                if stop_flag and stop_flag():
                    return
                key = (app_id, title, subtitle, body, delivered_date)
                if seen.add(key):
                    on_notification(app_id, title, subtitle, body, delivered_date)
            new_max = _max_delivered_date(batch)
            if new_max is not None:
                since_date = new_max
        except FileNotFoundError as exc:
            if on_error:
                on_error(exc)
        except Exception as exc:
            if on_error:
                on_error(exc)
        if _interruptible_sleep(_resolve_poll(poll_seconds), stop_flag):
            return
