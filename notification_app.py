#!/usr/bin/env python3
"""
Menu bar app for watching macOS Notification Center. Requires Full Disk Access.
"""
import queue
import subprocess
import threading
import time
from pathlib import Path

import rumps

import webhook_sender
from notification_watcher import (
    format_delivered_date,
    get_notification_db_path,
    iter_notifications,
)

RECENT_MAX = 10
QUEUE_DRAIN_INTERVAL = 0.5
FULL_DISK_URL = "x-apple.systempreferences:com.apple.preference.security?Privacy_AllFiles"


class NotificationWatcherApp(rumps.App):
    def __init__(self) -> None:
        super().__init__("NC", title="NC", quit_button=None)
        self._db_path: Path | None = get_notification_db_path()
        self._poll_seconds = 2.0
        self._app_filter: str | None = None
        self._discord_only = False
        self._notif_queue: queue.Queue = queue.Queue()
        self._stop_thread = threading.Event()
        self._recent: list[tuple[str, str, str, str, float | None]] = []
        self._seen: set[tuple[str, str, str, str, float | None]] = set()

        self.menu = [
            ["Recent", [rumps.MenuItem("(none)")]],
            None,
            rumps.MenuItem("Discord only", callback=self._toggle_discord),
            [
                "Poll interval",
                [
                    rumps.MenuItem("1 s", callback=self._set_poll),
                    rumps.MenuItem("2 s", callback=self._set_poll),
                    rumps.MenuItem("5 s", callback=self._set_poll),
                ],
            ],
            None,
            [
                "Webhooks",
                [
                    rumps.MenuItem("Add webhook URL...", callback=self._add_webhook),
                    rumps.MenuItem("Clear all webhooks", callback=self._clear_webhooks),
                    rumps.MenuItem("Open config file", callback=self._edit_webhook_config),
                ],
            ],
            None,
            "Quit",
        ]
        self._poll_menu = self.menu["Poll interval"]
        self._poll_menu["2 s"].state = True

        if self._db_path is None or not self._db_path.exists():
            rumps.alert(
                "Full Disk Access required",
                "Notification Watcher needs Full Disk Access to read notifications.\n\n"
                "System Settings will open. Add this app (or Terminal) to Full Disk Access.",
            )
            subprocess.run(["open", FULL_DISK_URL], check=False, timeout=5)
        else:
            self._start_watcher_thread()
            rumps.Timer(self._drain_queue, QUEUE_DRAIN_INTERVAL).start()

    def _toggle_discord(self, sender: rumps.MenuItem) -> None:
        self._discord_only = not sender.state
        sender.state = self._discord_only
        self._app_filter = "%discord%" if self._discord_only else None

    def _set_poll(self, sender: rumps.MenuItem) -> None:
        for item in self._poll_menu.values():
            if isinstance(item, rumps.MenuItem):
                item.state = item == sender
        label = sender.title
        if label == "1 s":
            self._poll_seconds = 1.0
        elif label == "2 s":
            self._poll_seconds = 2.0
        elif label == "5 s":
            self._poll_seconds = 5.0

    def _watcher_loop(self) -> None:
        while not self._stop_thread.is_set() and self._db_path and self._db_path.exists():
            try:
                for app_id, title, subtitle, body, _presented, delivered_date in iter_notifications(
                    self._db_path, self._app_filter
                ):
                    if self._stop_thread.is_set():
                        return
                    key = (app_id, title, subtitle, body, delivered_date)
                    if key not in self._seen:
                        self._seen.add(key)
                        self._notif_queue.put((app_id, title, subtitle, body, delivered_date))
            except FileNotFoundError:
                pass
            for _ in range(int(self._poll_seconds * 10)):
                if self._stop_thread.is_set():
                    return
                time.sleep(0.1)

    def _start_watcher_thread(self) -> None:
        t = threading.Thread(target=self._watcher_loop, daemon=True)
        t.start()

    def _add_webhook(self, _: rumps.MenuItem) -> None:
        window = rumps.Window(
            message="Enter webhook URL (Discord notifications will be POSTed here):",
            title="Add webhook",
            default_text="https://",
            ok="Add",
            cancel="Cancel",
        )
        response = window.run()
        if response.clicked == 1:
            url = (response.text or "").strip()
            if not url:
                rumps.alert("URL is empty.", "Add webhook")
                return
            if not url.startswith(("http://", "https://")):
                rumps.alert("URL must start with http:// or https://", "Add webhook")
                return
            urls = webhook_sender.load_webhook_urls()
            if url in urls:
                rumps.alert("That URL is already in the list.", "Add webhook")
                return
            urls.append(url)
            webhook_sender.save_webhook_urls(urls)
            rumps.notification("Notification Watcher", "Webhook added", url[:60] + "..." if len(url) > 60 else url)

    def _clear_webhooks(self, _: rumps.MenuItem) -> None:
        if not webhook_sender.load_webhook_urls():
            rumps.alert("No webhooks configured.", "Webhooks")
            return
        if rumps.alert("Clear all webhook URLs?", "Webhooks", ok="Clear all", cancel="Cancel") == 1:
            webhook_sender.save_webhook_urls([])
            rumps.notification("Notification Watcher", "All webhooks cleared", "All webhook URLs have been removed.")

    def _edit_webhook_config(self, _: rumps.MenuItem) -> None:
        path = webhook_sender.get_webhook_config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            webhook_sender.save_webhook_urls([])
        subprocess.run(["open", "-e", str(path)], check=False, timeout=5)

    def _drain_queue(self, _: rumps.Timer) -> None:
        while True:
            try:
                item = self._notif_queue.get_nowait()
            except queue.Empty:
                break
            app_id, title, subtitle, body, delivered_date = item
            webhook_sender.send_discord_notification(
                app_id, title, subtitle, body, delivered_date
            )
            self._recent.insert(0, item)
            self._recent = self._recent[:RECENT_MAX]
            self._rebuild_recent_menu()

    def _rebuild_recent_menu(self) -> None:
        recent_menu = self.menu["Recent"]
        for key in list(recent_menu.keys()):
            del recent_menu[key]
        if not self._recent:
            recent_menu["0"] = rumps.MenuItem("(none)")
            return
        for i, (app_id, title, subtitle, body, delivered_date) in enumerate(self._recent):
            label = f"{title or '(no title)'} — {app_id}" if app_id else (title or "(no title)")
            if len(label) > 60:
                label = label[:57] + "..."
            recent_menu[str(i)] = rumps.MenuItem(label)

    @rumps.clicked("Quit")
    def quit_app(self, _: rumps.MenuItem) -> None:
        self._stop_thread.set()
        rumps.quit_application()


def main() -> None:
    app = NotificationWatcherApp()
    app.run()


if __name__ == "__main__":
    main()
