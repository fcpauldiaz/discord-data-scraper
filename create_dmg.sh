#!/usr/bin/env bash
# Create a DMG for distributing Notification Watcher. Run after: python3 setup.py py2app
set -e
APP_NAME="Notification Watcher"
DMG_NAME="NotificationWatcher"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DIST_DIR="${SCRIPT_DIR}/dist"
VOLUME_NAME="${APP_NAME}"
DMG_PATH="${DIST_DIR}/${DMG_NAME}.dmg"

if [[ ! -d "${DIST_DIR}/${APP_NAME}.app" ]]; then
  echo "Run first: python3 setup.py py2app"
  exit 1
fi

rm -f "${DMG_PATH}"
hdiutil create -volname "${VOLUME_NAME}" -srcfolder "${DIST_DIR}/${APP_NAME}.app" -ov -format UDZO "${DMG_PATH}"
echo "Created ${DMG_PATH}"
