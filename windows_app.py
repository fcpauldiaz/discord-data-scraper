#!/usr/bin/env python3
"""
Windows system tray app for watching Action Center notifications.
"""
from __future__ import annotations

import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, simpledialog

import pystray
from PIL import Image, ImageDraw

import webhook_sender
from notification_watcher.config import get_config_path, get_log_path, load_config, save_config
from notification_watcher.login import is_launch_at_login_enabled, set_launch_at_login
from notification_watcher.platform import get_backend
from notification_watcher.types import AppConfig
from notification_watcher.watcher import watch
from notification_watcher.windows import format_delivered_date, get_notification_db_path

RECENT_MAX = 10
QUEUE_DRAIN_INTERVAL = 0.5
POLL_LABELS = {
    0.01: "10 ms",
    0.05: "50 ms",
    0.1: "100 ms",
    0.5: "500 ms",
    1.0: "1 s",
}
ASSETS_DIR = Path(__file__).resolve().parent / "assets"


def _load_icon() -> Image.Image:
    ico = ASSETS_DIR / "icon.ico"
    if ico.exists():
        return Image.open(ico)
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((8, 8, 56, 56), fill=(66, 133, 244, 255))
    draw.rectangle((30, 18, 34, 40), fill="white")
    draw.ellipse((26, 40, 38, 50), fill="white")
    return img


class WindowsNotificationApp:
    def __init__(self) -> None:
        self._config = load_config()
        self._db_path = get_notification_db_path()
        self._poll_seconds = self._config.poll_seconds
        self._app_filter = self._config.effective_app_filter()
        self._discord_only = self._config.discord_only
        self._notif_queue: queue.Queue = queue.Queue()
        self._stop_thread = threading.Event()
        self._watcher_thread: threading.Thread | None = None
        self._recent: list[tuple[str, str, str, str, float | None]] = []
        self._status = "Starting..."
        self._icon: pystray.Icon | None = None
        self._tk_root = tk.Tk()
        self._tk_root.withdraw()

        if self._db_path is None or not self._db_path.exists():
            messagebox.showinfo(
                "Notification Watcher",
                "Notification database not found yet.\n\n"
                "The app will watch:\n"
                "%LOCALAPPDATA%\\Microsoft\\Windows\\Notifications\\wpndatabase.db\n\n"
                "Send a test notification if watching does not start.",
            )

        self._start_background_tasks()
        self._build_tray()

    def _save_config(self) -> None:
        self._config.poll_seconds = self._poll_seconds
        self._config.discord_only = self._discord_only
        self._app_filter = self._config.effective_app_filter()
        save_config(self._config)

    def _set_status(self, status: str) -> None:
        self._status = status
        if self._icon:
            self._icon.update_menu()

    def _start_background_tasks(self) -> None:
        threading.Thread(target=self._drain_loop, daemon=True).start()
        threading.Thread(target=self._permission_loop, daemon=True).start()
        self._update_watcher()
        webhook_sender.get_app_logger().info("Windows app started (db=%s)", self._db_path)

    def _permission_loop(self) -> None:
        import time

        while not self._stop_thread.is_set():
            path = get_notification_db_path()
            exists = path is not None and path.exists()
            if exists and self._status.startswith(("Waiting", "Starting")):
                self._db_path = path
                self._set_status("Watching")
                self._update_watcher()
            elif not exists and self._status == "Watching":
                self._set_status("Waiting for notification database")
                self._stop_thread.set()
                self._stop_thread = threading.Event()
            time.sleep(5.0)

    def _update_watcher(self) -> None:
        if self._db_path is None or not self._db_path.exists():
            self._set_status("Waiting for notification database")
            return
        self._set_status("Watching")
        self._stop_thread.set()
        self._stop_thread = threading.Event()
        self._watcher_thread = threading.Thread(target=self._watcher_loop, daemon=True)
        self._watcher_thread.start()

    def _on_notification(
        self, app_id: str, title: str, subtitle: str, body: str, delivered_date: float | None
    ) -> None:
        self._notif_queue.put((app_id, title, subtitle, body, delivered_date))

    def _on_error(self, exc: Exception) -> None:
        self._set_status(f"Error: {exc}")

    def _watcher_loop(self) -> None:
        if not self._db_path:
            return
        backend = get_backend()

        def stop_flag() -> bool:
            return self._stop_thread.is_set()

        watch(
            backend,
            self._db_path,
            lambda: self._poll_seconds,
            lambda: self._app_filter,
            self._on_notification,
            stop_flag=stop_flag,
            on_error=self._on_error,
        )

    def _drain_loop(self) -> None:
        import time

        while True:
            while True:
                try:
                    item = self._notif_queue.get_nowait()
                except queue.Empty:
                    break
                app_id, title, subtitle, body, delivered_date = item
                webhook_sender.send_notification_webhook(
                    app_id, title, subtitle, body, delivered_date, self._config
                )
                self._recent.insert(0, item)
                self._recent = self._recent[:RECENT_MAX]
                if self._icon:
                    self._icon.update_menu()
            time.sleep(QUEUE_DRAIN_INTERVAL)

    def _build_tray(self) -> None:
        self._icon = pystray.Icon(
            "NotificationWatcher",
            _load_icon(),
            "Notification Watcher",
            menu=self._build_menu,
        )

    def _build_menu(self) -> pystray.Menu:
        items: list[pystray.MenuItem | pystray.Menu] = [
            pystray.MenuItem(f"Status: {self._status}", None, enabled=False),
            pystray.Menu.SEPARATOR,
        ]
        recent_items: list[pystray.MenuItem] = []
        if not self._recent:
            recent_items.append(pystray.MenuItem("(none)", None, enabled=False))
        else:
            recent_items = [
                pystray.MenuItem(
                    self._recent_label(i, item),
                    self._make_recent_handler(i),
                )
                for i, item in enumerate(self._recent)
            ]
        items.append(pystray.MenuItem("Recent", pystray.Menu(*recent_items)))
        items.append(pystray.Menu.SEPARATOR)
        items.append(
            pystray.MenuItem(
                "Discord only",
                self._toggle_discord,
                checked=lambda _: self._discord_only,
            )
        )
        items.append(pystray.MenuItem("Filter by app...", self._set_app_filter))
        poll_submenu = pystray.Menu(
            *[
                pystray.MenuItem(
                    label,
                    self._make_poll_handler(seconds),
                    checked=lambda _, s=seconds: self._poll_seconds == s,
                    radio=True,
                )
                for seconds, label in POLL_LABELS.items()
            ]
        )
        items.append(pystray.MenuItem("Poll interval", poll_submenu))
        items.append(pystray.Menu.SEPARATOR)
        items.append(
            pystray.MenuItem(
                "Launch at login",
                self._toggle_launch_at_login,
                checked=lambda _: is_launch_at_login_enabled(),
            )
        )
        items.append(pystray.Menu.SEPARATOR)
        items.append(
            pystray.MenuItem(
                "Webhooks",
                pystray.Menu(
                    pystray.MenuItem("Add webhook URL...", self._add_webhook),
                    pystray.MenuItem("Test webhook", self._test_webhook),
                    pystray.MenuItem("Clear all webhooks", self._clear_webhooks),
                    pystray.MenuItem("View logs", self._view_logs),
                    pystray.MenuItem("Open config file", self._edit_config),
                ),
            )
        )
        items.append(pystray.Menu.SEPARATOR)
        items.append(pystray.MenuItem("Quit", self._quit))
        return pystray.Menu(*items)

    def _recent_label(self, index: int, item: tuple[str, str, str, str, float | None]) -> str:
        app_id, title, _, _, _ = item
        label = f"{title or '(no title)'} — {app_id}" if app_id else (title or "(no title)")
        if len(label) > 55:
            label = label[:52] + "..."
        return f"{index + 1}. {label}"

    def _make_recent_handler(self, index: int):
        def handler(_icon, _item) -> None:
            self._show_recent_at(index)

        return handler

    def _make_poll_handler(self, seconds: float):
        def handler(_icon, _item) -> None:
            self._poll_seconds = seconds
            self._save_config()
            self._update_watcher()

        return handler

    def _show_recent_at(self, index: int) -> None:
        if index < 0 or index >= len(self._recent):
            return
        app_id, title, subtitle, body, delivered_date = self._recent[index]
        messagebox.showinfo(
            title or "Notification",
            f"App: {app_id}\n"
            f"Time: {format_delivered_date(delivered_date)}\n"
            f"Title: {title}\n"
            f"Subtitle: {subtitle}\n"
            f"Body: {body}",
        )

    def _toggle_discord(self, _icon, _item) -> None:
        self._discord_only = not self._discord_only
        self._config.discord_only = self._discord_only
        self._app_filter = self._config.effective_app_filter()
        self._save_config()
        self._update_watcher()

    def _set_app_filter(self, _icon, _item) -> None:
        value = simpledialog.askstring(
            "Filter by app",
            "App identifier filter (SQL LIKE, e.g. %discord%):",
            initialvalue=self._config.app_filter or "",
            parent=self._tk_root,
        )
        if value is None:
            return
        self._config.app_filter = value.strip() or None
        if self._config.app_filter:
            self._discord_only = False
            self._config.discord_only = False
        self._app_filter = self._config.effective_app_filter()
        self._save_config()
        self._update_watcher()

    def _toggle_launch_at_login(self, _icon, _item) -> None:
        enabled = not is_launch_at_login_enabled()
        set_launch_at_login(enabled, Path(sys.executable))
        self._config.launch_at_login = is_launch_at_login_enabled()
        save_config(self._config)

    def _add_webhook(self, _icon, _item) -> None:
        url = simpledialog.askstring(
            "Add webhook",
            "Enter HTTPS webhook URL:",
            initialvalue="https://",
            parent=self._tk_root,
        )
        if not url:
            return
        error = webhook_sender.validate_webhook_url(url.strip())
        if error:
            messagebox.showerror("Add webhook", error)
            return
        if url.strip() in self._config.webhook_urls:
            messagebox.showinfo("Add webhook", "That URL is already in the list.")
            return
        self._config.webhook_urls.append(url.strip())
        save_config(self._config)

    def _test_webhook(self, _icon, _item) -> None:
        ok, message = webhook_sender.send_test_webhook()
        if ok:
            messagebox.showinfo("Webhook test", message)
        else:
            messagebox.showerror("Webhook test failed", message)

    def _clear_webhooks(self, _icon, _item) -> None:
        if not self._config.webhook_urls:
            messagebox.showinfo("Webhooks", "No webhooks configured.")
            return
        if messagebox.askyesno("Webhooks", "Clear all webhook URLs?"):
            self._config.webhook_urls = []
            save_config(self._config)

    def _view_logs(self, _icon, _item) -> None:
        path = get_log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text("", encoding="utf-8")
        subprocess.run(["notepad.exe", str(path)], check=False)

    def _edit_config(self, _icon, _item) -> None:
        path = get_config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            save_config(self._config)
        subprocess.run(["notepad.exe", str(path)], check=False)

    def _quit(self, _icon, _item) -> None:
        self._stop_thread.set()
        if self._icon:
            self._icon.stop()
        self._tk_root.destroy()

    def run(self) -> None:
        if self._icon:
            self._icon.run()


def main() -> None:
    app = WindowsNotificationApp()
    app.run()


if __name__ == "__main__":
    main()
