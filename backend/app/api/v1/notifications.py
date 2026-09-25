from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.models import Notification, NotificationPreference, User
from app.db.session import get_db_session

router = APIRouter(prefix="/notifications", tags=["notifications"])


class PreferenceUpdate(BaseModel):
    locale: str = Field(default="en", pattern="^(en|hi)$")
    sms_enabled: bool = True
    email_enabled: bool = True
    in_app_enabled: bool = True


def _preference_response(preference: NotificationPreference) -> dict[str, object]:
    return {
        "locale": preference.locale,
        "sms_enabled": preference.sms_enabled,
        "email_enabled": preference.email_enabled,
        "in_app_enabled": preference.in_app_enabled,
    }


@router.get("/preferences")
async def get_preferences(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, object]:
    preference = await session.scalar(
        select(NotificationPreference).where(NotificationPreference.user_id == user.id)
    )
    if preference is None:
        preference = NotificationPreference(user_id=user.id)
        session.add(preference)
        await session.commit()
        await session.refresh(preference)
    return _preference_response(preference)


@router.patch("/preferences")
async def update_preferences(
    payload: PreferenceUpdate,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, object]:
    preference = await session.scalar(
        select(NotificationPreference).where(NotificationPreference.user_id == user.id)
    )
    if preference is None:
        preference = NotificationPreference(user_id=user.id)
        session.add(preference)
    for field, value in payload.model_dump().items():
        setattr(preference, field, value)
    await session.commit()
    await session.refresh(preference)
    return _preference_response(preference)


@router.get("/history")
async def notification_history(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    limit: int = 50,
) -> list[dict[str, object]]:
    rows = list(
        (
            await session.scalars(
                select(Notification)
                .where(Notification.user_id == user.id)
                .order_by(Notification.created_at.desc())
                .limit(min(max(limit, 1), 100))
            )
        ).all()
    )
    return [
        {
            "id": str(item.id),
            "channel": item.channel,
            "subject": item.subject,
            "message": item.message,
            "status": item.status,
            "template_key": item.template_key,
            "locale": item.locale,
            "retry_count": item.retry_count,
            "created_at": item.created_at,
            "sent_at": item.sent_at,
        }
        for item in rows
    ]
