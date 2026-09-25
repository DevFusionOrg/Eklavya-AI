from datetime import UTC, datetime

from sqlalchemy import select

from app.db.models import Award, FollowupRequirement
from app.db.session import async_session_factory
from app.worker import celery_app


@celery_app.task  # type: ignore[untyped-decorator]
def mark_overdue_followups() -> None:
    import asyncio

    asyncio.run(_mark_overdue_followups())


async def _mark_overdue_followups() -> None:
    async with async_session_factory() as session:
        rows = list(
            (
                await session.execute(
                    select(FollowupRequirement, Award)
                    .join(Award, Award.id == FollowupRequirement.award_id)
                    .where(
                        FollowupRequirement.status.in_(("UPCOMING", "SUBMITTED")),
                        FollowupRequirement.due_date < datetime.now(UTC),
                    )
                )
            ).all()
        )
        for requirement, award in rows:
            requirement.status = "OVERDUE"
            award.status = "ON_HOLD"
            award.hold_reason = f"Overdue follow-up: {requirement.name}"
        if rows:
            await session.commit()
