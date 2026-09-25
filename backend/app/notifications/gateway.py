import json
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Protocol
from urllib.request import Request, urlopen

from app.core.config import settings


@dataclass(frozen=True)
class NotificationMessage:
    channel: str
    recipient: str
    subject: str
    message: str


@dataclass(frozen=True)
class DeliveryResult:
    provider_message_id: str | None = None


class NotificationGateway(Protocol):
    def send(self, notification: NotificationMessage) -> DeliveryResult:
        """Deliver a notification through the configured provider."""


class ConsoleNotificationGateway:
    def __init__(self) -> None:
        self.sent: list[NotificationMessage] = []

    def send(self, notification: NotificationMessage) -> DeliveryResult:
        self.sent.append(notification)
        return DeliveryResult(provider_message_id="console")


class SmtpNotificationGateway:
    def send(self, notification: NotificationMessage) -> DeliveryResult:
        message = EmailMessage()
        message["From"] = settings.smtp_from
        message["To"] = notification.recipient
        message["Subject"] = notification.subject
        message.set_content(notification.message)
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as client:
            if settings.smtp_starttls:
                client.starttls()
            if settings.smtp_username:
                client.login(settings.smtp_username, settings.smtp_password)
            client.send_message(message)
        return DeliveryResult(provider_message_id="smtp")


class HttpSmsNotificationGateway:
    def send(self, notification: NotificationMessage) -> DeliveryResult:
        payload = json.dumps(
            {"to": notification.recipient, "message": notification.message}
        ).encode()
        request = Request(
            settings.sms_http_url,
            data=payload,
            headers={
                "Authorization": f"Bearer {settings.sms_http_token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urlopen(request, timeout=10) as response:
            body = json.loads(response.read() or b"{}")
        return DeliveryResult(provider_message_id=str(body.get("id", "http-sms")))
