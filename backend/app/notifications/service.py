import smtplib
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import (
    Applicant,
    Application,
    Notification,
    NotificationPreference,
    User,
)
from app.notifications.gateway import (
    ConsoleNotificationGateway,
    HttpSmsNotificationGateway,
    NotificationGateway,
    NotificationMessage,
    SmtpNotificationGateway,
)

TEMPLATES: dict[str, dict[str, dict[str, str]]] = {
    "deficiency": {
        "en": {
            "subject": "Action required on your application",
            "sms": "Eklavya.AI: {name}, action is needed on application {reference}. Sign in to view details.",
            "email": "Hello {name},\n\nAction is needed on application {reference}.\n\n{message}",
        },
        "hi": {
            "subject": "आपके आवेदन पर कार्रवाई आवश्यक है",
            "sms": "Eklavya.AI: {name}, आवेदन {reference} पर कार्रवाई आवश्यक है। विवरण देखने के लिए साइन इन करें।",
            "email": "नमस्ते {name},\n\nआवेदन {reference} पर कार्रवाई आवश्यक है।\n\n{message}",
        },
    },
    "selection": {
        "en": {
            "subject": "Your scholarship selection update",
            "sms": "Eklavya.AI: {name}, application {reference} has a selection update. Sign in to view details.",
            "email": "Hello {name},\n\nYour application {reference} has an update: {message}.",
        },
        "hi": {
            "subject": "आपके छात्रवृत्ति चयन की जानकारी",
            "sms": "Eklavya.AI: {name}, आवेदन {reference} में चयन संबंधी जानकारी है। विवरण देखने के लिए साइन इन करें।",
            "email": "नमस्ते {name},\n\nआवेदन {reference} की स्थिति में बदलाव हुआ है: {message}।",
        },
    },
    "followup": {
        "en": {
            "subject": "Follow-up requirement update",
            "sms": "Eklavya.AI: {name}, application {reference} has a follow-up update. Sign in to view details.",
            "email": "Hello {name},\n\nFollow-up update for application {reference}: {message}.",
        },
        "hi": {
            "subject": "अनुवर्ती आवश्यकता की जानकारी",
            "sms": "Eklavya.AI: {name}, आवेदन {reference} की अनुवर्ती जानकारी है। विवरण देखने के लिए साइन इन करें।",
            "email": "नमस्ते {name},\n\nआवेदन {reference} की अनुवर्ती जानकारी: {message}।",
        },
    },
}


def _gateway(channel: str) -> NotificationGateway:
    if channel == "EMAIL" and settings.email_driver == "smtp":
        return SmtpNotificationGateway()
    if channel == "SMS" and settings.sms_driver == "http":
        return HttpSmsNotificationGateway()
    return ConsoleNotificationGateway()


def _reference(application: Application) -> str:
    return str(application.id).split("-")[0].upper()


class NotificationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def send(
        self,
        user_id: Any,
        template_key: str,
        message: str,
        *,
        name: str,
        reference: str,
        locale: str | None = None,
        channels: tuple[str, ...] = ("IN_APP", "EMAIL", "SMS"),
    ) -> list[Notification]:
        preference = await self.session.scalar(
            select(NotificationPreference).where(
                NotificationPreference.user_id == user_id
            )
        )
        user = await self.session.get(User, user_id)
        applicant = await self.session.scalar(
            select(Applicant).where(Applicant.user_id == user_id)
        )
        language = locale or (preference.locale if preference else "en")
        if language not in {"en", "hi"}:
            language = "en"
        template = TEMPLATES.get(template_key, TEMPLATES["followup"])[language]
        recipients = {
            "IN_APP": str(user_id),
            "EMAIL": (applicant.email if applicant else None)
            or (user.email if user else None),
            "SMS": applicant.phone if applicant else None,
        }
        enabled = {
            "IN_APP": preference.in_app_enabled if preference else True,
            "EMAIL": preference.email_enabled if preference else True,
            "SMS": preference.sms_enabled if preference else True,
        }
        created: list[Notification] = []
        for channel in channels:
            recipient = recipients.get(channel)
            if not recipient or not enabled[channel]:
                continue
            body = template["sms" if channel == "SMS" else "email"].format(
                name=name, reference=reference, message=message
            )
            notification = Notification(
                user_id=user_id,
                channel=channel,
                subject=template["subject"],
                message=body,
                status="PENDING",
                template_key=template_key,
                locale=language,
            )
            self.session.add(notification)
            await self.session.flush()
            try:
                result = _gateway(channel).send(
                    NotificationMessage(channel, recipient, template["subject"], body)
                )
                notification.status = "SENT"
                notification.sent_at = datetime.now(UTC)
                notification.provider_message_id = result.provider_message_id
            except (OSError, RuntimeError, ValueError, smtplib.SMTPException) as error:
                notification.status = "FAILED"
                notification.retry_count += 1
                notification.last_error = str(error)[:1000]
            created.append(notification)
        return created


async def notify_deficiency(
    session: AsyncSession, application: Application, message: str
) -> None:
    applicant = await session.scalar(
        select(Applicant).where(Applicant.id == application.applicant_id)
    )
    if applicant is None or applicant.user_id is None:
        return
    await NotificationService(session).send(
        applicant.user_id,
        "deficiency",
        message,
        name=applicant.full_name,
        reference=_reference(application),
    )


async def set_correction_deadline(
    application: Application, validation_config: dict[str, Any]
) -> None:
    days = int(
        validation_config.get(
            "correction_deadline_days", settings.correction_deadline_days
        )
    )
    application.correction_deadline = datetime.now(UTC) + timedelta(days=days)


async def notify_applicant(
    session: AsyncSession,
    application: Application,
    message: str,
    template_key: str = "deficiency",
) -> None:
    applicant = await session.scalar(
        select(Applicant).where(Applicant.id == application.applicant_id)
    )
    if applicant is None or applicant.user_id is None:
        return
    await NotificationService(session).send(
        applicant.user_id,
        template_key,
        message,
        name=applicant.full_name,
        reference=_reference(application),
    )
