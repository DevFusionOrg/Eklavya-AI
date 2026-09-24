import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.applications.state_machine import assert_transition
from app.audit.service import AuditService
from app.core.errors import DomainError
from app.db.models import Application, ApplicationStatusHistory


class ApplicationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def transition(
        self,
        application: Application,
        *,
        target: str,
        actor_id: uuid.UUID | None,
        actor_role: str,
        reason: str | None = None,
    ) -> Application:
        source = application.status
        if source == target:
            return application
        assert_transition(source, target, actor_role)
        application.status = target
        self.session.add(
            ApplicationStatusHistory(
                application_id=application.id,
                from_status=source,
                to_status=target,
                actor_id=actor_id,
                actor_role=actor_role,
                reason=reason,
            )
        )
        await AuditService(self.session).append(
            actor_id=actor_id,
            actor_role=actor_role,
            action="APPLICATION_STATUS_CHANGED",
            entity_type="APPLICATION",
            entity_id=application.id,
            before={"status": source},
            after={"status": target},
            reason=reason,
        )
        return application

    async def get_for_update(self, application_id: uuid.UUID) -> Application:
        application = await self.session.scalar(
            select(Application)
            .where(Application.id == application_id)
            .with_for_update()
        )
        if application is None:
            raise DomainError("APPLICATION_NOT_FOUND", "Application not found", 404)
        return application


def validate_form_data(
    form_schema: dict[str, Any],
    form_data: dict[str, Any],
    *,
    require_all: bool = True,
) -> list[str]:
    errors: list[str] = []
    required = form_schema.get("required", []) if require_all else []
    properties = form_schema.get("properties", {})
    for field in required:
        if field not in form_data or form_data[field] in (None, ""):
            errors.append(f"{field} is required")
    for field, definition in properties.items():
        if field not in form_data or "type" not in definition:
            continue
        value = form_data[field]
        expected = definition["type"]
        valid = (
            (expected == "string" and isinstance(value, str))
            or (
                expected == "number"
                and isinstance(value, (int, float))
                and not isinstance(value, bool)
            )
            or (
                expected == "integer"
                and isinstance(value, int)
                and not isinstance(value, bool)
            )
            or (expected == "boolean" and isinstance(value, bool))
            or (expected == "array" and isinstance(value, list))
            or (expected == "object" and isinstance(value, dict))
        )
        if not valid:
            errors.append(f"{field} must be a {expected}")
    return errors
