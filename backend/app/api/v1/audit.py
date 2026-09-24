from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import AuditService
from app.auth.dependencies import require_roles
from app.db.models import User
from app.db.session import get_db_session

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/verify")
async def verify_audit_chain(
    _: Annotated[User, Depends(require_roles("ADMIN"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, object]:
    return await AuditService(session).verify()
