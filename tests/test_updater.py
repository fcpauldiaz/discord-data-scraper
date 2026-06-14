from notification_watcher.updater import (
    ReleaseInfo,
    is_newer_version,
    parse_version,
)


def test_parse_version():
    assert parse_version("1.2.3") == (1, 2, 3)
    assert parse_version("v2.0.1") == (2, 0, 1)
    assert parse_version("bad") is None


def test_is_newer_version():
    assert is_newer_version("1.2.0", "1.1.0") is True
    assert is_newer_version("1.1.0", "1.1.0") is False
    assert is_newer_version("1.0.9", "1.1.0") is False
    assert is_newer_version("2.0.0", "1.9.9") is True


def test_release_info_frozen():
    info = ReleaseInfo(
        version="1.2.0",
        tag="v1.2.0",
        download_url="https://example.com/app.dmg",
        asset_name="NotificationWatcher-1.2.0.dmg",
        release_notes="Fixes",
    )
    assert info.version == "1.2.0"
