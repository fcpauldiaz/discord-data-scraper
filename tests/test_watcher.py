from notification_watcher.watcher import SeenTracker


def test_seen_tracker_dedup():
    tracker = SeenTracker(max_size=10)
    key = ("app", "title", "sub", "body", 1.0)
    assert tracker.add(key) is True
    assert tracker.add(key) is False


def test_seen_tracker_eviction():
    tracker = SeenTracker(max_size=2)
    assert tracker.add(("a", "t", "s", "b", 1.0)) is True
    assert tracker.add(("b", "t", "s", "b", 2.0)) is True
    assert tracker.add(("c", "t", "s", "b", 3.0)) is True
    assert tracker.add(("a", "t", "s", "b", 1.0)) is True
