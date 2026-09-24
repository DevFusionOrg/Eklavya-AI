import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Applicant, Application, User


async def owned_application_for_user(
    application_id: uuid.UUID, user: User, session: AsyncSession
) -> Application:
    application = await session.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    if user.role == "APPLICANT":
        applicant = await session.scalar(
            select(Applicant).where(Applicant.user_id == user.id)
        )
        if applicant is None or applicant.id != application.applicant_id:
            raise HTTPException(status_code=404, detail="Application not found")
    return application
