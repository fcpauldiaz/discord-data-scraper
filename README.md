# Notification Watcher – Mac menu bar app

Menu bar app that watches macOS Notification Center and shows recent notifications. Requires **Full Disk Access** (System Settings → Privacy & Security).

## Build the app

```bash
cd /path/to/notification-watcher
pip install -r requirements-app.txt
python3 setup.py py2app
```

Output: `dist/Notification Watcher.app`

## Create a DMG for distribution

```bash
./create_dmg.sh
```

Creates `dist/NotificationWatcher.dmg`. Share this file; users drag the app to Applications.

## First run

1. Open **Notification Watcher.app** (or run `python3 notification_app.py` from this directory).
2. If the Notification Center database is not found, the app shows an alert and opens System Settings. Add **Terminal** (or **Notification Watcher**) to **Full Disk Access**.
3. Click the **NC** icon in the menu bar to see Recent notifications, Discord-only toggle, and Poll interval.

## Signing and notarization (optional)

For distribution without Gatekeeper warnings:

1. Sign: `codesign -s "Developer ID Application: Your Name" "dist/Notification Watcher.app"`
2. Notarize with Apple (xcrun notarize-tool or Xcode Organizer), then staple the ticket.

Without notarization, users may need to right-click → Open the first time.
