import uuid
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.applications.service import ApplicationService
from app.audit.service import AuditService
from app.auth.dependencies import require_roles
from app.core.config import settings
from app.core.errors import DomainError
from app.db.models import (
    AiRecommendation,
    Application,
    ApplicationDocument,
    Deficiency,
    ExtractedField,
    ReviewAction,
    Scheme,
    SchemeVersion,
    User,
)
from app.db.session import get_db_session
from app.rules.engine import evaluate
from app.storage.service import MinioDocumentStorage

router = APIRouter(prefix="/officer", tags=["officer"])
OFFICER_ROLES = ("SCRUTINY_OFFICER", "VERIFYING_OFFICER", "ADMIN")


class OfficerAction(BaseModel):
    action: Literal["VERIFY", "RAISE_DEFICIENCY", "REJECT", "ESCALATE"]
    reason_code: str | None = Field(default=None, min_length=2, max_length=64)
    remarks: str | None = Field(default=None, max_length=2000)
    field: str | None = None
    document_id: uuid.UUID | None = None
    severity: str = "HIGH"
    override_source: Literal["NONE", "AI", "RULES"] = "NONE"


def _role_dependency() -> Any:
    return require_roles(*OFFICER_ROLES)


async def _application(session: AsyncSession, application_id: uuid.UUID) -> Application:
    item = await session.scalar(
        select(Application).where(Application.id == application_id).with_for_update()
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return item


@router.get("/queue")
async def scrutiny_queue(
    user: Annotated[User, Depends(_role_dependency())],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    scheme: str | None = None,
    state: str | None = None,
    status: str = "UNDER_SCRUTINY",
    deficiency_severity: str | None = None,
    confidence_band: str | None = Query(default=None, pattern="^(LOW|MEDIUM|HIGH)$"),
    sort: str = Query(default="created_at", pattern="^(created_at|confidence)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any]:
    query = (
        select(Application, Scheme.code)
        .join(SchemeVersion, SchemeVersion.id == Application.scheme_version_id)
        .join(Scheme, Scheme.id == SchemeVersion.scheme_id)
        .where(Application.status == status)
    )
    if user.role == "SCRUTINY_OFFICER":
        query = query.where(
            (Application.scrutiny_officer_id.is_(None))
            | (Application.scrutiny_officer_id == user.id)
        )
    elif user.role == "VERIFYING_OFFICER":
        query = query.where(
            Application.verifying_officer_id.is_(None)
            | (Application.verifying_officer_id == user.id)
        )
    if scheme:
        query = query.where(Scheme.code == scheme)
    if state:
        query = query.where(Application.status == state)
    if deficiency_severity:
        query = query.join(
            Deficiency,
            Deficiency.application_id == Application.id,
        ).where(
            Deficiency.status == "OPEN",
            Deficiency.severity == deficiency_severity,
        )
    if confidence_band:
        query = query.join(
            ApplicationDocument, ApplicationDocument.application_id == Application.id
        )
        query = query.join(
            ExtractedField, ExtractedField.document_id == ApplicationDocument.id
        )
        if confidence_band == "LOW":
            query = query.where(ExtractedField.confidence < 0.75)
        elif confidence_band == "MEDIUM":
            query = query.where(
                ExtractedField.confidence >= 0.75, ExtractedField.confidence < 0.9
            )
        else:
            query = query.where(ExtractedField.confidence >= 0.9)
    count_query = select(func.count()).select_from(query.subquery())
    total = int(await session.scalar(count_query) or 0)
    query = (
        query.order_by(
            Application.created_at.desc()
            if sort == "created_at"
            else Application.updated_at.desc()
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await session.execute(query)).all()
    return {
        "items": [
            {
                "id": str(application.id),
                "scheme": code,
                "status": application.status,
                "scrutiny_officer_id": (
                    str(application.scrutiny_officer_id)
                    if application.scrutiny_officer_id
                    else None
                ),
                "verifying_officer_id": (
                    str(application.verifying_officer_id)
                    if application.verifying_officer_id
                    else None
                ),
            }
            for application, code in rows
        ],
        "page": page,
        "page_size": page_size,
        "total": total,
    }


@router.post("/applications/{application_id}/claim")
async def claim_application(
    application_id: uuid.UUID,
    user: Annotated[User, Depends(_role_dependency())],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    application = await _application(session, application_id)
    if user.role == "SCRUTINY_OFFICER":
        if application.scrutiny_officer_id not in (None, user.id):
            raise DomainError(
                "APPLICATION_ALREADY_ASSIGNED",
                "Application is assigned to another officer",
                409,
            )
        application.scrutiny_officer_id = user.id
    elif user.role == "VERIFYING_OFFICER":
        if application.verifying_officer_id not in (None, user.id):
            raise DomainError(
                "APPLICATION_ALREADY_ASSIGNED",
                "Application is assigned to another officer",
                409,
            )
        if application.scrutiny_officer_id == user.id:
            raise DomainError(
                "ROLE_SEPARATION_VIOLATION",
                "An officer cannot verify their own scrutiny work",
                409,
            )
        application.verifying_officer_id = user.id
    else:
        raise HTTPException(
            status_code=403, detail="Administrators cannot claim applications"
        )
    await AuditService(session).append(
        actor_id=user.id,
        actor_role=user.role,
        action="APPLICATION_CLAIMED",
        entity_type="APPLICATION",
        entity_id=application.id,
        after={"role": user.role, "officer_id": str(user.id)},
    )
    await session.commit()
    return {"id": str(application.id), "claimed_by": str(user.id), "role": user.role}


@router.get("/applications/{application_id}/review")
async def review_payload(
    application_id: uuid.UUID,
    user: Annotated[User, Depends(_role_dependency())],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    application = await _application(session, application_id)
    documents = list(
        (
            await session.scalars(
                select(ApplicationDocument).where(
                    ApplicationDocument.application_id == application.id
                )
            )
        ).all()
    )
    fields = list(
        (
            await session.scalars(
                select(ExtractedField)
                .join(ApplicationDocument)
                .where(ApplicationDocument.application_id == application.id)
            )
        ).all()
    )
    version = await session.get(SchemeVersion, application.scheme_version_id)
    rules = evaluate(
        version.eligibility_rules if version else {},
        {
            "form_data": application.form_data,
            "extracted_fields": {field.field: field.value for field in fields},
        },
    )
    recommendations = list(
        (
            await session.scalars(
                select(AiRecommendation)
                .where(AiRecommendation.application_id == application.id)
                .order_by(AiRecommendation.created_at.desc())
            )
        ).all()
    )
    return {
        "application": {
            "id": str(application.id),
            "status": application.status,
            "form_data": application.form_data,
        },
        "documents": [
            {
                "id": str(document.id),
                "doc_type": document.doc_type,
                "mime": document.mime,
                "ocr_status": document.ocr_status,
                "signed_url": MinioDocumentStorage().presigned_get(document.object_key),
                "expires_in": settings.document_url_expiry_seconds,
            }
            for document in documents
        ],
        "extracted_fields": [
            {
                "field": field.field,
                "value": field.value,
                "confidence": float(field.confidence or 0),
                "bbox": field.source_bbox,
                "document_id": str(field.document_id),
            }
            for field in fields
        ],
        "rules": [result.as_dict() for result in rules],
        "ai_recommendation": recommendations[0].output if recommendations else None,
    }


@router.post("/applications/{application_id}/actions")
async def officer_action(
    application_id: uuid.UUID,
    payload: OfficerAction,
    user: Annotated[User, Depends(_role_dependency())],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    application = await _application(session, application_id)
    if payload.action in {"REJECT", "RAISE_DEFICIENCY"} and not payload.reason_code:
        raise DomainError("REASON_REQUIRED", "A reason code is required", 422)
    if payload.action == "REJECT" and not payload.remarks:
        raise DomainError("REMARKS_REQUIRED", "Remarks are required for rejection", 422)
    if payload.override_source != "NONE" and not payload.remarks:
        raise DomainError(
            "OVERRIDE_REASON_REQUIRED",
            "A reason is required when overriding AI or rules",
            422,
        )
    version = await session.get(SchemeVersion, application.scheme_version_id)
    validation_rules = version.rules if version else {}
    two_level = bool(validation_rules.get("two_level_signoff", True))
    if user.role == "VERIFYING_OFFICER" and application.scrutiny_officer_id == user.id:
        raise DomainError(
            "ROLE_SEPARATION_VIOLATION",
            "An officer cannot sign off their own scrutiny work",
            409,
        )
    if user.role == "SCRUTINY_OFFICER" and application.scrutiny_officer_id not in (
        None,
        user.id,
    ):
        raise DomainError(
            "NOT_ASSIGNED", "Application is assigned to another scrutiny officer", 403
        )
    if payload.action == "ESCALATE":
        if user.role != "SCRUTINY_OFFICER":
            raise HTTPException(
                status_code=403, detail="Only scrutiny officers can escalate"
            )
        application.verifying_officer_id = None
    elif payload.action == "VERIFY":
        if user.role != "VERIFYING_OFFICER" and not (
            user.role == "SCRUTINY_OFFICER" and not two_level
        ):
            raise HTTPException(
                status_code=403, detail="Only verifying officers can sign off"
            )
        await ApplicationService(session).transition(
            application,
            target="OFFICER_VERIFIED",
            actor_id=user.id,
            actor_role=user.role,
            reason=payload.remarks or "Human verification passed",
        )
    elif payload.action == "RAISE_DEFICIENCY":
        session.add(
            Deficiency(
                application_id=application.id,
                code=payload.reason_code or "OFFICER_DEFICIENCY",
                message=payload.remarks or "Officer raised a deficiency",
                severity=payload.severity,
                status="OPEN",
                raised_by_type="OFFICER",
                raised_by_id=user.id,
                field=payload.field,
                document_id=payload.document_id,
            )
        )
        await ApplicationService(session).transition(
            application,
            target="DEFICIENT",
            actor_id=user.id,
            actor_role=user.role,
            reason=payload.remarks,
        )
    elif payload.action == "REJECT":
        await ApplicationService(session).transition(
            application,
            target="NOT_SELECTED",
            actor_id=user.id,
            actor_role=user.role,
            reason=f"{payload.reason_code}: {payload.remarks}",
        )
    await session.flush()
    session.add(
        ReviewAction(
            application_id=application.id,
            officer_id=user.id,
            action=payload.action,
            remarks=f"{payload.reason_code or ''}: {payload.remarks or ''}",
            override_source=payload.override_source,
        )
    )
    await AuditService(session).append(
        actor_id=user.id,
        actor_role=user.role,
        action=f"OFFICER_{payload.action}",
        entity_type="APPLICATION",
        entity_id=application.id,
        after={
            "reason_code": payload.reason_code,
            "remarks": payload.remarks,
            "status": application.status,
            "override_source": payload.override_source,
        },
        reason=payload.remarks,
    )
    await session.commit()
    return {
        "id": str(application.id),
        "status": application.status,
        "action": payload.action,
    }
