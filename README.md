# Notification Watcher

Cross-platform utility that watches OS notifications and optionally forwards them to HTTPS webhooks.

| Platform | Supported versions | Data source |
|----------|-------------------|-------------|
| macOS | 13+ (Sequoia/Tahoe may need FDA) | Notification Center SQLite |
| Windows | 10, 11 | `%LOCALAPPDATA%\Microsoft\Windows\Notifications\wpndatabase.db` |

## Features

- Menu bar (macOS) or system tray (Windows) UI
- Recent notifications list with detail view
- Configurable poll interval: 10 ms, 50 ms, 100 ms, 500 ms, 1 s
- App filter (SQL LIKE) and Discord-only shortcut
- Webhooks: Discord embed format (auto-detected) or generic JSON
- Persistent settings, launch at login, local logs
- CLI (`scraper.py`) for scripting

## Quick start

### macOS (from source)

```bash
pip install -r requirements-app.txt
python3 scripts/generate_icons.py
python3 notification_app.py
```

Grant **Full Disk Access** to Terminal or Notification Watcher in System Settings → Privacy & Security.

### Windows (from source)

```bash
pip install -r requirements-windows.txt
python scripts/generate_icons.py
python windows_app.py
```

### CLI (either platform)

```bash
python3 scraper.py                  # watch + webhooks
python3 scraper.py --once           # dump once
python3 scraper.py --discord-only
python3 scraper.py --poll 0.5
python3 scraper.py --no-webhook
```

Config file location:

- macOS: `~/Library/Application Support/Notification Watcher/config.json`
- Windows: `%APPDATA%\Notification Watcher\config.json`

## Build distributables

### macOS .app and DMG

```bash
pip install -r requirements-app.txt
python3 scripts/generate_icons.py
python3 setup.py py2app
./create_dmg.sh
```

Output: `dist/Notification Watcher.app`, `dist/NotificationWatcher-1.1.0.dmg`

### Windows .exe

```bash
pip install -r requirements-windows.txt
python scripts/generate_icons.py
pyinstaller notification_watcher.spec
```

Output: `dist/NotificationWatcher/NotificationWatcher.exe`

## CI artifacts

GitHub Actions runs tests on every push/PR. On pushes to `main`, it also builds macOS and Windows artifacts, creates a **`v{version}` tag** from [`notification_watcher/version.py`](notification_watcher/version.py), and publishes a [GitHub Release](https://github.com/fcpauldiaz/discord-data-scraper/releases) with download links for:

- `NotificationWatcher-{version}.dmg` (macOS)
- `NotificationWatcher-{version}-win.zip` (Windows)

Bump `__version__` in `notification_watcher/version.py` before merging to `main` to publish a new release tag.

## Signing (local)

Unsigned CI builds are fine for personal use. For distribution:

```bash
# macOS — set SIGN_IDENTITY and NOTARY_PROFILE (notarytool keychain profile)
SIGN_IDENTITY="Developer ID Application: Your Name" ./scripts/sign_and_notarize_mac.sh

# Windows — set WINDOWS_CERT_PATH and optional WINDOWS_CERT_PASSWORD
./scripts/sign_windows.ps1
```

## Webhook format

- URLs matching `discord.com/api/webhooks` receive Discord **embed** payloads.
- Other HTTPS URLs receive generic JSON: `app_id`, `title`, `subtitle`, `body`, `delivered_date`, `platform`.
- Set `"webhook_format": "discord"` or `"generic"` in config to override auto-detect.
- Set `"webhook_discord_only": true` to forward only Discord app notifications.

## Troubleshooting

### macOS: no notifications

1. Confirm Full Disk Access is enabled for the app.
2. Check status in the menu: should say **Watching**.
3. Open logs via Webhooks → View logs.

### Windows: no notifications

1. Confirm `wpndatabase.db` exists under `%LOCALAPPDATA%\Microsoft\Windows\Notifications\`.
2. Send a test toast; WAL mode may add slight delay.
3. Check `%APPDATA%\Notification Watcher\notification_watcher.log`.

### Webhooks fail

- Use HTTPS public URLs only (localhost/private IPs are blocked).
- For Discord, use a full webhook URL from Server Settings → Integrations.
- Use Webhooks → Test webhook to verify.

## Uninstall

### macOS

1. Quit the app.
2. Delete `Notification Watcher.app` from Applications.
3. Remove `~/Library/Application Support/Notification Watcher/`.
4. Remove `~/Library/LaunchAgents/com.notificationwatcher.app.plist` if present.

### Windows

1. Quit the tray app.
2. Delete the install folder.
3. Remove `%APPDATA%\Notification Watcher\`.
4. Remove the `NotificationWatcher` entry from Registry → `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` if present.

## Privacy

See [PRIVACY.md](PRIVACY.md). No telemetry.

## Auto-update

Bundled macOS and Windows builds check [GitHub Releases](https://github.com/fcpauldiaz/discord-data-scraper/releases) for updates:

- **On startup** (after 60 seconds) and **once per day**
- **Manual check**: menu bar / tray → **Updates → Check for updates...**
- **macOS**: downloads the DMG, installs to `/Applications`, offers restart
- **Windows**: downloads the zip, applies on quit via a small updater script, then relaunches
- **Running from source**: opens the release download page instead of installing in place

Disable automatic checks in `config.json`:

```json
{ "check_for_updates": false }
```

CI also publishes `appcast.xml` on each release for optional future [Sparkle](https://sparkle-project.org/) integration (`SUFeedURL` is set in the macOS app plist).

## License

MIT — see [LICENSE](LICENSE).
