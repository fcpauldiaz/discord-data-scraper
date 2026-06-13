import webhook_sender


def test_is_discord_webhook_url():
    assert webhook_sender.is_discord_webhook_url(
        "https://discord.com/api/webhooks/123/abc"
    )
    assert webhook_sender.is_discord_webhook_url(
        "https://discordapp.com/api/webhooks/123/abc"
    )
    assert not webhook_sender.is_discord_webhook_url("https://example.com/hook")


def test_resolve_webhook_format_auto():
    assert (
        webhook_sender.resolve_webhook_format(
            "https://discord.com/api/webhooks/1/x", "auto"
        )
        == "discord"
    )
    assert (
        webhook_sender.resolve_webhook_format("https://example.com/hook", "auto")
        == "generic"
    )


def test_build_discord_payload():
    payload = webhook_sender.build_discord_payload(
        "com.discord", "Title", "Sub", "Body", None
    )
    assert "embeds" in payload
    assert payload["embeds"][0]["title"] == "Title"
    assert "Sub" in payload["embeds"][0]["description"]
    assert payload["embeds"][0]["footer"]["text"] == "com.discord"


def test_build_generic_payload():
    payload = webhook_sender.build_generic_payload(
        "com.app", "Title", "Sub", "Body", None
    )
    assert payload["app_id"] == "com.app"
    assert payload["title"] == "Title"
    assert "platform" in payload
