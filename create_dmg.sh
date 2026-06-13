#!/usr/bin/env bash
# Create a DMG for distributing Notification Watcher. Run after: python3 setup.py py2app
set -euo pipefail
APP_NAME="Notification Watcher"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DIST_DIR="${SCRIPT_DIR}/dist"
VERSION="$(python3 -c "from notification_watcher.version import __version__; print(__version__)")"
DMG_NAME="NotificationWatcher-${VERSION}"
STAGING="${DIST_DIR}/dmg-staging"
DMG_PATH="${DIST_DIR}/${DMG_NAME}.dmg"

if [[ ! -d "${DIST_DIR}/${APP_NAME}.app" ]]; then
  echo "Run first: python3 setup.py py2app"
  exit 1
fi

rm -rf "${STAGING}"
mkdir -p "${STAGING}"
cp -R "${DIST_DIR}/${APP_NAME}.app" "${STAGING}/"
ln -s /Applications "${STAGING}/Applications"
rm -f "${DMG_PATH}"
hdiutil create -volname "${APP_NAME}" -srcfolder "${STAGING}" -ov -format UDZO "${DMG_PATH}"
rm -rf "${STAGING}"
echo "Created ${DMG_PATH}"
