import hashlib
import json
import uuid
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditLog


def canonical_row(
    *,
    actor_id: uuid.UUID | None,
    actor_role: str | None,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID,
    before: Mapping[str, Any] | None,
    after: Mapping[str, Any] | None,
    reason: str | None,
    ip: str | None,
    request_id: str | None,
    created_at: datetime,
    prev_hash: str | None,
) -> str:
    payload = {
        "action": action,
        "actor_id": str(actor_id) if actor_id else None,
        "actor_role": actor_role,
        "after": after,
        "before": before,
        "created_at": created_at.astimezone(UTC).isoformat(),
        "entity_id": str(entity_id),
        "entity_type": entity_type,
        "ip": ip,
        "prev_hash": prev_hash,
        "reason": reason,
        "request_id": request_id,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def hash_row(**kwargs: Any) -> str:
    return hashlib.sha256(canonical_row(**kwargs).encode("utf-8")).hexdigest()


class AuditService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def append(
        self,
        *,
        actor_id: uuid.UUID | None,
        actor_role: str | None,
        action: str,
        entity_type: str,
        entity_id: uuid.UUID,
        before: Mapping[str, Any] | None = None,
        after: Mapping[str, Any] | None = None,
        reason: str | None = None,
        ip: str | None = None,
        request_id: str | None = None,
    ) -> AuditLog:
        previous = await self.session.scalar(
            select(AuditLog)
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .with_for_update()
        )
        created_at = datetime.now(UTC)
        prev_hash = previous.row_hash if previous else None
        row = AuditLog(
            actor_id=actor_id,
            actor_role=actor_role,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            before=dict(before) if before else None,
            after=dict(after) if after else None,
            reason=reason,
            ip=ip,
            request_id=request_id,
            created_at=created_at,
            prev_hash=prev_hash,
            row_hash=hash_row(
                actor_id=actor_id,
                actor_role=actor_role,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                before=before,
                after=after,
                reason=reason,
                ip=ip,
                request_id=request_id,
                created_at=created_at,
                prev_hash=prev_hash,
            ),
        )
        self.session.add(row)
        return row

    async def verify(self) -> dict[str, Any]:
        rows = (
            await self.session.scalars(
                select(AuditLog).order_by(AuditLog.created_at.asc(), AuditLog.id.asc())
            )
        ).all()
        previous_hash: str | None = None
        for position, row in enumerate(rows):
            expected = hash_row(
                actor_id=row.actor_id,
                actor_role=row.actor_role,
                action=row.action,
                entity_type=row.entity_type,
                entity_id=row.entity_id,
                before=row.before,
                after=row.after,
                reason=row.reason,
                ip=row.ip,
                request_id=row.request_id,
                created_at=row.created_at,
                prev_hash=row.prev_hash,
            )
            if row.prev_hash != previous_hash or row.row_hash != expected:
                return {
                    "valid": False,
                    "first_broken_link": {
                        "position": position,
                        "audit_id": str(row.id),
                    },
                }
            previous_hash = row.row_hash
        return {"valid": True, "rows_checked": len(rows), "first_broken_link": None}
