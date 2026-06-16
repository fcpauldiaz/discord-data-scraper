import json
import urllib.error
import urllib.request

from notification_watcher.product import DEFAULT_INGEST_URL, DEFAULT_PLATFORM_URL


class AuthError(Exception):
    pass


def sign_in(email: str, password: str, platform_url: str | None = None) -> dict[str, str]:
    base = (platform_url or DEFAULT_PLATFORM_URL).rstrip("/")
    payload = json.dumps({"email": email, "password": password}).encode("utf-8")
    req = urllib.request.Request(
        f"{base}/api/desktop/auth",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            body = json.loads(exc.read().decode("utf-8"))
            message = body.get("error", "Sign in failed")
        except (json.JSONDecodeError, OSError):
            message = "Sign in failed"
        raise AuthError(message) from exc
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        raise AuthError(f"Could not reach platform: {exc}") from exc

    api_key = data.get("api_key")
    ingest_url = data.get("ingest_url") or DEFAULT_INGEST_URL
    account_email = data.get("email") or email
    if not api_key:
        raise AuthError("Platform did not return a device token")
    return {
        "auth_token": api_key,
        "ingest_url": ingest_url,
        "account_email": account_email,
    }
