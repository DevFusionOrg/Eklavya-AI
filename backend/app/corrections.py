from datetime import UTC, datetime

from sqlalchemy import select

from app.applications.service import ApplicationService
from app.db.models import Application
from app.db.session import async_session_factory
from app.worker import celery_app


@celery_app.task  # type: ignore[untyped-decorator]
def expire_correction_deadlines() -> None:
    import asyncio

    asyncio.run(_expire_deadlines())


async def _expire_deadlines() -> None:
    async with async_session_factory() as session:
        applications = list(
            (
                await session.scalars(
                    select(Application).where(
                        Application.status == "DEFICIENT",
                        Application.correction_deadline < datetime.now(UTC),
                    )
                )
            ).all()
        )
        for application in applications:
            await ApplicationService(session).transition(
                application,
                target="CLOSED",
                actor_id=None,
                actor_role="SYSTEM",
                reason="Correction deadline expired",
            )
        if applications:
            await session.commit()
