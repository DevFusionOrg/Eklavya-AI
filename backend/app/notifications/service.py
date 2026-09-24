from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import Applicant, Application, Notification, User
from app.notifications.gateway import (
    ConsoleNotificationGateway,
    NotificationGateway,
    NotificationMessage,
)


def _gateway() -> NotificationGateway:
    return ConsoleNotificationGateway()


async def notify_deficiency(
    session: AsyncSession, application: Application, message: str
) -> None:
    applicant = await session.scalar(
        select(Applicant).where(Applicant.id == application.applicant_id)
    )
    if applicant is None or applicant.user_id is None:
        return
    user = await session.get(User, applicant.user_id)
    recipients = [
        ("IN_APP", str(applicant.user_id)),
        ("EMAIL", applicant.email or (user.email if user else "")),
    ]
    if applicant.phone:
        recipients.append(("SMS", applicant.phone))
    gateway = _gateway()
    for channel, recipient in recipients:
        if not recipient:
            continue
        notification = Notification(
            user_id=applicant.user_id,
            channel=channel,
            subject="Action required on your application",
            message=message,
            status="PENDING",
        )
        session.add(notification)
        gateway.send(
            NotificationMessage(channel, recipient, notification.subject or "", message)
        )


async def notify_applicant(
    session: AsyncSession, application: Application, message: str
) -> None:
    await notify_deficiency(session, application, message)


async def set_correction_deadline(
    application: Application, validation_config: dict[str, Any]
) -> None:
    days = int(
        validation_config.get(
            "correction_deadline_days", settings.correction_deadline_days
        )
    )
    application.correction_deadline = datetime.now(UTC) + timedelta(days=days)
