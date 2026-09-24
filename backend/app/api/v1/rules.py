import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_roles
from app.db.models import Scheme, User
from app.db.session import get_db_session
from app.rules.engine import evaluate
from app.rules.selection import select_candidates

router = APIRouter(prefix="/schemes", tags=["rules"])


class RulesDryRunRequest(BaseModel):
    rules: list[dict[str, Any]] = Field(default_factory=list)
    context: dict[str, Any] = Field(default_factory=dict)
    selection: dict[str, Any] | None = None
    candidates: list[dict[str, Any]] = Field(default_factory=list)


@router.post("/{scheme_id}/rules/dry-run")
async def dry_run_rules(
    scheme_id: uuid.UUID,
    payload: RulesDryRunRequest,
    _: Annotated[User, Depends(require_roles("ADMIN"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    if await session.get(Scheme, scheme_id) is None:
        raise HTTPException(status_code=404, detail="Scheme not found")
    results = [result.as_dict() for result in evaluate(payload.rules, payload.context)]
    response: dict[str, Any] = {"results": results}
    if payload.selection is not None:
        response["selection"] = select_candidates(payload.candidates, payload.selection)
    return response
