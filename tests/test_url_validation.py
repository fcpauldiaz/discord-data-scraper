import webhook_sender


def test_validate_webhook_url_rejects_insecure():
    assert webhook_sender.validate_webhook_url("http://example.com/hook") is not None


def test_validate_webhook_url_rejects_localhost():
    assert webhook_sender.validate_webhook_url("https://localhost/hook") is not None


def test_validate_webhook_url_rejects_private_ip():
    assert webhook_sender.validate_webhook_url("https://192.168.1.5/hook") is not None


def test_validate_webhook_url_accepts_public():
    assert webhook_sender.validate_webhook_url("https://example.com/hook") is None
