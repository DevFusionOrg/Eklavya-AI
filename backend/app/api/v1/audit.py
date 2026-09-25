from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import AuditService
from app.auth.dependencies import require_roles
from app.db.models import AuditLog, User
from app.db.session import get_db_session

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/verify")
async def verify_audit_chain(
    _: Annotated[User, Depends(require_roles("ADMIN"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, object]:
    return await AuditService(session).verify()


@router.get("/history")
async def audit_history(
    _: Annotated[User, Depends(require_roles("ADMIN"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    limit: int = Query(default=100, ge=1, le=500),
) -> list[dict[str, object]]:
    rows = list(
        (
            await session.scalars(
                select(AuditLog)
                .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
                .limit(limit)
            )
        ).all()
    )
    return [
        {
            "id": str(row.id),
            "actor_role": row.actor_role,
            "action": row.action,
            "entity_type": row.entity_type,
            "entity_id": str(row.entity_id),
            "reason": row.reason,
            "created_at": row.created_at,
            "row_hash": row.row_hash,
        }
        for row in rows
    ]
