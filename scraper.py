#!/usr/bin/env python3
"""
CLI for watching macOS Notification Center. Uses notification_watcher for core logic.
"""
import argparse
from pathlib import Path

import webhook_sender
from notification_watcher import (
    format_delivered_date,
    get_notification_db_path,
    iter_notifications,
    watch,
)


def print_notification(
    app_id: str,
    title: str,
    subtitle: str,
    body: str,
    delivered_date,
) -> None:
    print("=" * 50)
    print(f"App:       {app_id}")
    print(f"Time:      {format_delivered_date(delivered_date)}")
    print(f"Title:     {title}")
    print(f"Subtitle:  {subtitle}")
    print(f"Body:      {body}")
    print("=" * 50)


def run_once(db_path: Path, app_filter: str | None) -> None:
    count = 0
    for app_id, title, subtitle, body, _presented, delivered_date in iter_notifications(
        db_path, app_filter
    ):
        print_notification(app_id, title, subtitle, body, delivered_date)
        count += 1
    if count == 0:
        print("No notifications found.")


def run_watch(
    db_path: Path,
    poll_seconds: float,
    app_filter: str | None,
    no_webhook: bool = False,
) -> None:
    print("Watching for new notifications... (Ctrl+C to stop)\n")

    def on_notification(app_id: str, title: str, subtitle: str, body: str, delivered_date):
        print_notification(app_id, title, subtitle, body, delivered_date)
        if not no_webhook:
            webhook_sender.send_discord_notification(
                app_id, title, subtitle, body, delivered_date
            )

    try:
        watch(db_path, poll_seconds, app_filter, on_notification)
    except KeyboardInterrupt:
        print("\nStopped.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Watch macOS Notification Center for new notifications (never-ending loop)."
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Print current notifications once and exit instead of watching.",
    )
    parser.add_argument(
        "--discord-only",
        action="store_true",
        help="Only show notifications from apps whose identifier contains 'discord'.",
    )
    parser.add_argument(
        "--poll",
        type=float,
        default=2.0,
        metavar="SECONDS",
        help="Poll interval in seconds (default: 2.0).",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=None,
        metavar="PATH",
        help="Path to Notification Center db (default: auto-detect).",
    )
    parser.add_argument(
        "--no-webhook",
        action="store_true",
        help="Do not send Discord notifications to configured webhook URLs.",
    )
    args = parser.parse_args()

    db_path = args.db or get_notification_db_path()
    if not db_path:
        print("Could not resolve Notification Center database path (getconf DARWIN_USER_DIR failed).")
        raise SystemExit(1)

    app_filter = "%discord%" if args.discord_only else None

    try:
        if args.once:
            run_once(db_path, app_filter)
        else:
            run_watch(db_path, args.poll, app_filter, no_webhook=args.no_webhook)
    except FileNotFoundError as e:
        print(e)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
