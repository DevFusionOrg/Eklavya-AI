from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class NotificationMessage:
    channel: str
    recipient: str
    subject: str
    message: str


class NotificationGateway(Protocol):
    def send(self, notification: NotificationMessage) -> None:
        """Deliver a notification through the configured provider."""


class ConsoleNotificationGateway:
    def __init__(self) -> None:
        self.sent: list[NotificationMessage] = []

    def send(self, notification: NotificationMessage) -> None:
        self.sent.append(notification)
