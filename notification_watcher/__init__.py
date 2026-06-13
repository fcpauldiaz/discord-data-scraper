from notification_watcher.platform import get_backend
from notification_watcher.types import DeliveredDate, Notification, OnNotification
from notification_watcher.version import __version__
from notification_watcher.watcher import SeenTracker, watch

_backend = None


def _get():
    global _backend
    if _backend is None:
        _backend = get_backend()
    return _backend


def get_notification_db_path():
    return _get().get_notification_db_path()


def iter_notifications(db_path, app_filter=None, since_date=None):
    return _get().iter_notifications(db_path, app_filter, since_date=since_date)


def format_delivered_date(delivered_date):
    return _get().format_delivered_date(delivered_date)


def to_unix_timestamp(delivered_date):
    return _get().to_unix_timestamp(delivered_date)


__all__ = [
    "__version__",
    "DeliveredDate",
    "Notification",
    "OnNotification",
    "SeenTracker",
    "format_delivered_date",
    "get_backend",
    "get_notification_db_path",
    "iter_notifications",
    "to_unix_timestamp",
    "watch",
]
