from dataclasses import dataclass, field
from typing import Callable, Literal

DeliveredDate = float | None
Notification = tuple[str, str, str, str, int | None, DeliveredDate]
OnNotification = Callable[[str, str, str, str, DeliveredDate], None]
OnError = Callable[[Exception], None]
WebhookFormat = Literal["auto", "discord", "generic"]


@dataclass
class AppConfig:
    webhook_urls: list[str] = field(default_factory=list)
    poll_seconds: float = 0.5
    discord_only: bool = False
    app_filter: str | None = None
    webhook_discord_only: bool = False
    launch_at_login: bool = False
    webhook_format: WebhookFormat = "auto"

    def effective_app_filter(self) -> str | None:
        if self.discord_only:
            return "%discord%"
        return self.app_filter
