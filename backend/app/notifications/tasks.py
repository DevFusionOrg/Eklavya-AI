import smtplib
from datetime import UTC, datetime

from sqlalchemy import select

from app.core.config import settings
from app.db.models import Applicant, Notification
from app.db.session import async_session_factory
from app.notifications.gateway import NotificationMessage
from app.notifications.service import _gateway
from app.worker import celery_app


@celery_app.task(bind=True, max_retries=settings.notification_max_retries)
def retry_failed_notifications(task, limit: int = 100) -> None:  # type: ignore[no-untyped-def]
    import asyncio

    try:
        asyncio.run(_retry(limit))
    except Exception as error:
        raise task.retry(exc=error, countdown=60) from error


async def _retry(limit: int) -> None:
    async with async_session_factory() as session:
        rows = list(
            (
                await session.scalars(
                    select(Notification)
                    .where(
                        Notification.status == "FAILED",
                        Notification.retry_count < settings.notification_max_retries,
                    )
                    .order_by(Notification.created_at.asc())
                    .limit(limit)
                )
            ).all()
        )
        for notification in rows:
            applicant = await session.scalar(
                select(Applicant).where(Applicant.user_id == notification.user_id)
            )
            recipient = (
                str(notification.user_id)
                if notification.channel == "IN_APP"
                else (
                    (applicant.email if applicant else None)
                    if notification.channel == "EMAIL"
                    else (applicant.phone if applicant else None)
                )
            )
            if not recipient:
                continue
            try:
                result = _gateway(notification.channel).send(
                    NotificationMessage(
                        notification.channel,
                        recipient,
                        notification.subject or "",
                        notification.message,
                    )
                )
                notification.status = "SENT"
                notification.sent_at = datetime.now(UTC)
                notification.provider_message_id = result.provider_message_id
            except (OSError, RuntimeError, ValueError, smtplib.SMTPException) as error:
                notification.retry_count += 1
                notification.last_error = str(error)[:1000]
        if rows:
            await session.commit()
