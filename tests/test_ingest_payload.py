import ingest_sender


def test_build_generic_payload():
    payload = ingest_sender.build_generic_payload(
        "com.app", "Title", "Sub", "Body", None
    )
    assert payload["app_id"] == "com.app"
    assert payload["title"] == "Title"
    assert "platform" in payload
