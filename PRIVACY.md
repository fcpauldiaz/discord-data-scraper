# Privacy Policy

Notification Watcher is a local utility. It does not operate a cloud service or collect analytics.

## What the app reads

- **macOS**: Notification content from the local Notification Center SQLite database (app identifier, title, subtitle, body, delivery time). Requires Full Disk Access.
- **Windows**: Notification content from the local `wpndatabase.db` file (app identifier, toast text, arrival time).

## What leaves your device

- If you configure **webhook URLs**, matching notification data is sent via HTTPS POST to those endpoints only.
- No data is sent if no webhooks are configured.

## What is stored locally

- Settings: `config.json` in the app support directory.
- Logs: `notification_watcher.log` in the same directory (webhook attempts, errors).

## Third parties

Webhook destinations (e.g. Discord, your own server) are chosen by you. Their privacy policies apply to data you send them.

## Telemetry

This app does not include telemetry, crash reporting, or automatic update checks in v1.1.0.

## Contact

For privacy questions, open an issue in the project repository.
