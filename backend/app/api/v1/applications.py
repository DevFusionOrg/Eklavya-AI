import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.applications.service import ApplicationService, validate_form_data
from app.auth.dependencies import get_current_user, require_roles
from app.core.config import settings
from app.core.errors import DomainError
from app.db.models import (
    Applicant,
    Application,
    ApplicationStatusHistory,
    Deficiency,
    Scheme,
    SchemeVersion,
    User,
)
from app.db.session import get_db_session

router = APIRouter(prefix="/applications", tags=["applications"])


class DraftCreate(BaseModel):
    scheme_version_id: uuid.UUID
    form_data: dict[str, Any] = Field(default_factory=dict)


class DraftUpdate(BaseModel):
    form_data: dict[str, Any] = Field(default_factory=dict)


async def get_applicant(
    user: Annotated[User, Depends(require_roles("APPLICANT"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Applicant:
    applicant = await session.scalar(
        select(Applicant).where(Applicant.user_id == user.id)
    )
    if applicant is None:
        applicant = Applicant(user_id=user.id, full_name=user.email, email=user.email)
        session.add(applicant)
        await session.flush()
    return applicant


async def owned_application(
    application_id: uuid.UUID,
    applicant: Applicant,
    session: AsyncSession,
) -> Application:
    application = await session.get(Application, application_id)
    if application is None or application.applicant_id != applicant.id:
        raise HTTPException(status_code=404, detail="Application not found")
    return application


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_draft(
    payload: DraftCreate,
    applicant: Annotated[Applicant, Depends(get_applicant)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    version = await session.get(SchemeVersion, payload.scheme_version_id)
    if version is None or version.status != "PUBLISHED":
        raise HTTPException(
            status_code=409, detail="Scheme version is not accepting applications"
        )
    application = Application(
        applicant_id=applicant.id,
        scheme_version_id=version.id,
        form_data=payload.form_data,
    )
    session.add(application)
    await session.commit()
    await session.refresh(application)
    return {
        "id": str(application.id),
        "status": application.status,
        "scheme_version_id": str(version.id),
    }


@router.patch("/{application_id}")
async def autosave_draft(
    application_id: uuid.UUID,
    payload: DraftUpdate,
    applicant: Annotated[Applicant, Depends(get_applicant)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    application = await owned_application(application_id, applicant, session)
    if application.status not in {"DRAFT", "DEFICIENT"}:
        raise DomainError(
            "APPLICATION_NOT_EDITABLE",
            "Only draft or deficient applications can be edited",
            409,
        )
    if application.status == "DEFICIENT":
        flagged = set(
            (
                await session.scalars(
                    select(Deficiency.field).where(
                        Deficiency.application_id == application.id,
                        Deficiency.status == "OPEN",
                        Deficiency.field.is_not(None),
                    )
                )
            ).all()
        )
        forbidden = set(payload.form_data) - flagged
        if forbidden:
            raise DomainError(
                "FIELD_NOT_FLAGGED",
                f"Only flagged fields can be corrected: {', '.join(sorted(forbidden))}",
                422,
            )
    version = await session.get(SchemeVersion, application.scheme_version_id)
    if version is None:
        raise DomainError("SCHEME_VERSION_NOT_FOUND", "Scheme version not found", 409)
    merged_data = {**application.form_data, **payload.form_data}
    if errors := validate_form_data(
        version.form_schema, merged_data, require_all=False
    ):
        raise DomainError(
            "PARTIAL_FORM_VALIDATION_FAILED",
            f"Some saved fields are invalid: {', '.join(errors)}",
            422,
        )
    application.form_data = merged_data
    await session.commit()
    return {
        "id": str(application.id),
        "status": application.status,
        "form_data": application.form_data,
    }


@router.post("/{application_id}/resubmit")
async def resubmit_application(
    application_id: uuid.UUID,
    applicant: Annotated[Applicant, Depends(get_applicant)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    application = await owned_application(application_id, applicant, session)
    if application.status != "DEFICIENT":
        raise DomainError(
            "APPLICATION_NOT_DEFICIENT", "Application has no corrections due", 409
        )
    version = await session.get(SchemeVersion, application.scheme_version_id)
    if version is None:
        raise DomainError("SCHEME_VERSION_NOT_FOUND", "Scheme version not found", 409)
    config = version.rules.get("validation", {})
    max_rounds = int(
        config.get("max_correction_rounds", settings.max_correction_rounds)
    )
    if application.correction_round >= max_rounds:
        await ApplicationService(session).transition(
            application,
            target="CLOSED",
            actor_id=None,
            actor_role="SYSTEM",
            reason="Maximum correction rounds exceeded",
        )
        await session.commit()
        raise DomainError(
            "CORRECTION_ROUNDS_EXCEEDED", "Maximum correction rounds exceeded", 409
        )
    if (
        application.correction_deadline
        and application.correction_deadline < datetime.now(UTC)
    ):
        raise DomainError(
            "CORRECTION_DEADLINE_EXPIRED", "Correction deadline has expired", 409
        )
    application.correction_round += 1
    await ApplicationService(session).transition(
        application,
        target="RESUBMITTED",
        actor_id=applicant.user_id,
        actor_role="APPLICANT",
        reason=f"Correction round {application.correction_round} submitted",
    )
    from app.validation.service import validate_application

    await validate_application(session, application.id)
    await session.commit()
    return {
        "id": str(application.id),
        "status": application.status,
        "correction_round": application.correction_round,
    }


@router.post("/{application_id}/submit")
async def submit_application(
    application_id: uuid.UUID,
    applicant: Annotated[Applicant, Depends(get_applicant)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    application = await session.scalar(
        select(Application)
        .where(
            Application.id == application_id,
            Application.applicant_id == applicant.id,
        )
        .with_for_update()
    )
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    if application.status == "SUBMITTED":
        return {"id": str(application.id), "status": application.status}
    version = await session.get(SchemeVersion, application.scheme_version_id)
    if version is None:
        raise DomainError("SCHEME_VERSION_NOT_FOUND", "Scheme version not found", 409)
    errors = validate_form_data(version.form_schema, application.form_data)
    if errors:
        raise DomainError(
            "FORM_VALIDATION_FAILED", "Complete required application fields", 422
        )
    await ApplicationService(session).transition(
        application,
        target="SUBMITTED",
        actor_id=applicant.user_id,
        actor_role="APPLICANT",
        reason="Applicant submitted application",
    )
    await session.commit()
    return {"id": str(application.id), "status": application.status}


@router.post("/{application_id}/withdraw")
async def withdraw_application(
    application_id: uuid.UUID,
    applicant: Annotated[Applicant, Depends(get_applicant)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    application = await owned_application(application_id, applicant, session)
    await ApplicationService(session).transition(
        application,
        target="CLOSED",
        actor_id=applicant.user_id,
        actor_role="APPLICANT",
        reason="Applicant withdrew application",
    )
    await session.commit()
    return {"id": str(application.id), "status": application.status}


@router.get("")
async def my_applications(
    applicant: Annotated[Applicant, Depends(get_applicant)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[dict[str, Any]]:
    applications = list(
        (
            await session.scalars(
                select(Application)
                .where(Application.applicant_id == applicant.id)
                .order_by(Application.created_at.desc())
            )
        ).all()
    )
    versions = {
        version_id: (code, name)
        for version_id, code, name in (
            await session.execute(
                select(SchemeVersion.id, Scheme.code, Scheme.name)
                .join(Scheme, Scheme.id == SchemeVersion.scheme_id)
                .where(
                    SchemeVersion.id.in_(
                        {item.scheme_version_id for item in applications}
                    )
                )
            )
        ).all()
    }
    return [
        {
            "id": str(item.id),
            "status": item.status,
            "scheme_version_id": str(item.scheme_version_id),
            "scheme_code": versions.get(item.scheme_version_id, ("", ""))[0],
            "scheme_name": versions.get(item.scheme_version_id, ("", ""))[1],
            "form_data": item.form_data,
            "correction_round": item.correction_round,
            "correction_deadline": item.correction_deadline,
        }
        for item in applications
    ]


@router.get("/{application_id}/deficiencies")
async def application_deficiencies(
    application_id: uuid.UUID,
    applicant: Annotated[Applicant, Depends(get_applicant)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    application = await owned_application(application_id, applicant, session)
    items = list(
        (
            await session.scalars(
                select(Deficiency)
                .where(Deficiency.application_id == application.id)
                .order_by(Deficiency.created_at.asc())
            )
        ).all()
    )
    cycles = max(application.correction_round, 0)
    return {
        "repeat_deficiency_cycles": cycles,
        "correction_round": application.correction_round,
        "correction_deadline": application.correction_deadline,
        "items": [
            {
                "id": str(item.id),
                "code": item.code,
                "message": item.message,
                "field": item.field,
                "document_id": str(item.document_id) if item.document_id else None,
                "severity": item.severity,
                "status": item.status,
            }
            for item in items
        ],
    }


@router.get("/{application_id}/timeline")
async def application_timeline(
    application_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[dict[str, Any]]:
    application = await session.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    if user.role == "APPLICANT":
        applicant = await session.scalar(
            select(Applicant).where(Applicant.user_id == user.id)
        )
        if applicant is None or applicant.id != application.applicant_id:
            raise HTTPException(status_code=404, detail="Application not found")
    history = list(
        (
            await session.scalars(
                select(ApplicationStatusHistory)
                .where(ApplicationStatusHistory.application_id == application_id)
                .order_by(ApplicationStatusHistory.created_at.asc())
            )
        ).all()
    )
    return [
        {
            "from_status": item.from_status,
            "to_status": item.to_status,
            "reason": item.reason,
            "created_at": item.created_at,
        }
        for item in history
    ]
