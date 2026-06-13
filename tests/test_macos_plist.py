import plistlib

from notification_watcher.macos import parse_notification_plist


def _plist_bytes(data: dict) -> bytes:
    return plistlib.dumps(data)


def test_parse_notification_plist_full():
    data = {
        "req": {
            "titl": "Hello",
            "subt": "World",
            "body": "Message body",
        }
    }
    parsed = parse_notification_plist(_plist_bytes(data))
    assert parsed == {"title": "Hello", "subtitle": "World", "body": "Message body"}


def test_parse_notification_plist_alt_keys():
    data = {"req": {"title": "T", "subtitle": "S", "message": "M"}}
    parsed = parse_notification_plist(_plist_bytes(data))
    assert parsed["title"] == "T"
    assert parsed["subtitle"] == "S"
    assert parsed["body"] == "M"


def test_parse_notification_plist_invalid():
    parsed = parse_notification_plist(b"not a plist")
    assert parsed == {"title": "", "subtitle": "", "body": ""}


def test_parse_notification_plist_empty_req():
    parsed = parse_notification_plist(_plist_bytes({}))
    assert parsed == {"title": "", "subtitle": "", "body": ""}
