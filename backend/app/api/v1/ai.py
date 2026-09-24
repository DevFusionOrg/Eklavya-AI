import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.service import generate_recommendation
from app.auth.dependencies import require_roles
from app.db.models import User
from app.db.session import get_db_session

router = APIRouter(prefix="/applications", tags=["ai"])


@router.post("/{application_id}/ai-recommendation")
async def create_ai_recommendation(
    application_id: uuid.UUID,
    user: Annotated[
        User,
        Depends(
            require_roles(
                "SCRUTINY_OFFICER", "VERIFYING_OFFICER", "COMMITTEE_MEMBER", "ADMIN"
            )
        ),
    ],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    recommendation = await generate_recommendation(session, application_id)
    return recommendation.model_dump()


@router.get("/{application_id}/ai-recommendations")
async def list_ai_recommendations(
    application_id: uuid.UUID,
    user: Annotated[
        User,
        Depends(
            require_roles(
                "SCRUTINY_OFFICER", "VERIFYING_OFFICER", "COMMITTEE_MEMBER", "ADMIN"
            )
        ),
    ],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[dict[str, Any]]:
    from sqlalchemy import select

    from app.db.models import AiRecommendation

    rows = list(
        (
            await session.scalars(
                select(AiRecommendation)
                .where(AiRecommendation.application_id == application_id)
                .order_by(AiRecommendation.created_at.desc())
            )
        ).all()
    )
    return [
        {
            "id": str(row.id),
            "model": row.model,
            "prompt_hash": row.prompt_hash,
            "response_hash": row.response_hash,
            "output": row.output,
            "confidence": float(row.confidence) if row.confidence is not None else None,
            "created_at": row.created_at,
        }
        for row in rows
    ]
