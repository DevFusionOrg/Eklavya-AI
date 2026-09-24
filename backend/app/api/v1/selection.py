import uuid
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.applications.service import ApplicationService
from app.audit.service import AuditService
from app.auth.dependencies import require_roles
from app.core.errors import DomainError
from app.db.models import (
    Application,
    ApplicationDocument,
    ExtractedField,
    SchemeVersion,
    Selection,
    User,
)
from app.db.session import get_db_session
from app.notifications.service import notify_applicant
from app.selection import export_csv, export_pdf, export_xlsx, rank_candidates

router = APIRouter(prefix="/selection", tags=["selection"])


class CommitteeAdjustment(BaseModel):
    list_status: Literal["SELECTED", "WAITLISTED", "NOT_SELECTED"]
    remarks: str = Field(min_length=1, max_length=2000)


async def _version(session: AsyncSession, application: Application) -> SchemeVersion:
    version = await session.get(SchemeVersion, application.scheme_version_id)
    if version is None:
        raise DomainError("SCHEME_VERSION_NOT_FOUND", "Scheme version not found", 409)
    return version


async def _candidate(session: AsyncSession, application: Application) -> dict[str, Any]:
    fields = list(
        (
            await session.scalars(
                select(ExtractedField)
                .join(ApplicationDocument)
                .where(ApplicationDocument.application_id == application.id)
            )
        ).all()
    )
    extracted = {field.field: field.value for field in fields}
    candidate: dict[str, Any] = {
        "id": str(application.id),
        "application_id": str(application.id),
        "form_data": application.form_data,
        "extracted_fields": extracted,
    }
    candidate.update(application.form_data)
    candidate.update(extracted)
    return candidate


async def _committee(
    user: Annotated[User, Depends(require_roles("COMMITTEE_MEMBER", "ADMIN"))],
) -> User:
    return user


@router.post("/schemes/{scheme_id}/run")
async def run_selection(
    scheme_id: uuid.UUID,
    user: Annotated[User, Depends(_committee)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    versions = await session.scalars(
        select(SchemeVersion)
        .where(
            SchemeVersion.scheme_id == scheme_id, SchemeVersion.status == "PUBLISHED"
        )
        .order_by(SchemeVersion.version_number.desc())
    )
    version = next(iter(versions), None)
    if version is None:
        raise HTTPException(
            status_code=404, detail="Published scheme version not found"
        )
    applications = list(
        (
            await session.scalars(
                select(Application)
                .where(
                    Application.scheme_version_id == version.id,
                    Application.status == "OFFICER_VERIFIED",
                )
                .order_by(Application.id.asc())
            )
        ).all()
    )
    config = version.selection_rules or {}
    candidates = [await _candidate(session, item) for item in applications]
    ranked = rank_candidates(candidates, config)
    existing = list(
        (
            await session.scalars(
                select(Selection)
                .join(Application)
                .where(Application.scheme_version_id == version.id)
            )
        ).all()
    )
    if any(item.is_frozen for item in existing):
        raise DomainError(
            "SELECTION_FROZEN", "The selection list is already frozen", 409
        )
    await session.execute(
        delete(Selection).where(
            Selection.application_id.in_([item.id for item in applications])
        )
    )
    for item in ranked:
        selection = Selection(
            application_id=uuid.UUID(item["application_id"]),
            selected_by=user.id,
            rank=item["rank"],
            list_status=item["list_status"],
            score=item["selection"]["score"],
            score_breakdown={
                "components": item["selection"]["components"],
                "rules": item["selection"]["results"],
            },
            remarks="Deterministic scheme rule run",
        )
        session.add(selection)
    await AuditService(session).append(
        actor_id=user.id,
        actor_role=user.role,
        action="SELECTION_LIST_GENERATED",
        entity_type="SCHEME_VERSION",
        entity_id=version.id,
        after={"candidate_count": len(ranked)},
    )
    await session.commit()
    return {"scheme_version_id": str(version.id), "items": ranked}


@router.get("/schemes/{scheme_id}/list")
async def selection_list(
    scheme_id: uuid.UUID,
    user: Annotated[User, Depends(_committee)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[dict[str, Any]]:
    rows = list(
        (
            await session.scalars(
                select(Selection)
                .join(Application)
                .join(SchemeVersion)
                .where(SchemeVersion.scheme_id == scheme_id)
                .order_by(Selection.rank.asc())
            )
        ).all()
    )
    return [
        {
            "application_id": str(row.application_id),
            "rank": row.rank,
            "status": row.list_status,
            "score": float(row.score or 0),
            "score_breakdown": row.score_breakdown,
            "remarks": row.remarks,
            "frozen": row.is_frozen,
        }
        for row in rows
    ]


@router.patch("/applications/{application_id}")
async def adjust_selection(
    application_id: uuid.UUID,
    payload: CommitteeAdjustment,
    user: Annotated[User, Depends(_committee)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    row = await session.scalar(
        select(Selection)
        .where(Selection.application_id == application_id)
        .with_for_update()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Selection candidate not found")
    if row.is_frozen:
        raise DomainError(
            "SELECTION_FROZEN", "Frozen selections cannot be adjusted", 409
        )
    row.list_status = payload.list_status
    row.remarks = payload.remarks
    await AuditService(session).append(
        actor_id=user.id,
        actor_role=user.role,
        action="SELECTION_ADJUSTED",
        entity_type="APPLICATION",
        entity_id=application_id,
        after={"list_status": payload.list_status, "remarks": payload.remarks},
        reason=payload.remarks,
    )
    await session.commit()
    return {"application_id": str(application_id), "status": row.list_status}


@router.post("/schemes/{scheme_id}/freeze")
async def freeze_selection(
    scheme_id: uuid.UUID,
    user: Annotated[User, Depends(_committee)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    rows = list(
        (
            await session.scalars(
                select(Selection)
                .join(Application)
                .join(SchemeVersion)
                .where(SchemeVersion.scheme_id == scheme_id)
                .with_for_update()
            )
        ).all()
    )
    if not rows:
        raise DomainError("SELECTION_EMPTY", "Generate a provisional list first", 409)
    for row in rows:
        row.is_frozen = True
    await AuditService(session).append(
        actor_id=user.id,
        actor_role=user.role,
        action="SELECTION_LIST_FROZEN",
        entity_type="SCHEME",
        entity_id=scheme_id,
        after={"count": len(rows)},
        reason="Committee froze final provisional list",
    )
    await session.commit()
    return {"scheme_id": str(scheme_id), "frozen": True, "count": len(rows)}


@router.post("/schemes/{scheme_id}/approve")
async def approve_selection(
    scheme_id: uuid.UUID,
    user: Annotated[User, Depends(require_roles("ADMIN"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    rows = list(
        (
            await session.scalars(
                select(Selection)
                .join(Application)
                .join(SchemeVersion)
                .where(SchemeVersion.scheme_id == scheme_id)
                .with_for_update()
            )
        ).all()
    )
    if not rows or not all(row.is_frozen for row in rows):
        raise DomainError(
            "SELECTION_NOT_FROZEN", "Freeze the list before approval", 409
        )
    counts = {"SELECTED": 0, "WAITLISTED": 0, "NOT_SELECTED": 0}
    for row in rows:
        application = await session.get(Application, row.application_id)
        if application is None:
            continue
        target = row.list_status
        if target not in counts:
            raise DomainError(
                "INVALID_SELECTION_STATUS", "Invalid final list status", 422
            )
        await ApplicationService(session).transition(
            application,
            target=target,
            actor_id=user.id,
            actor_role=user.role,
            reason="Authorised approval of frozen committee list",
        )
        counts[target] += 1
        await notify_applicant(
            session,
            application,
            f"Selection result: {target}. Please check your application.",
        )
    await AuditService(session).append(
        actor_id=user.id,
        actor_role=user.role,
        action="SELECTION_LIST_APPROVED",
        entity_type="SCHEME",
        entity_id=scheme_id,
        after=counts,
        reason="Authorised approver approved frozen list",
    )
    await session.commit()
    return {"scheme_id": str(scheme_id), "approved": True, "counts": counts}


@router.get("/schemes/{scheme_id}/export")
async def export_selection(
    scheme_id: uuid.UUID,
    user: Annotated[User, Depends(_committee)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    format: Literal["csv", "xlsx", "pdf"] = Query(default="csv"),
) -> Response:
    rows = list(
        (
            await session.scalars(
                select(Selection)
                .join(Application)
                .join(SchemeVersion)
                .where(SchemeVersion.scheme_id == scheme_id)
                .order_by(Selection.rank.asc())
            )
        ).all()
    )
    payload = [
        {
            "rank": row.rank,
            "application_id": str(row.application_id),
            "list_status": row.list_status,
            "score": float(row.score or 0),
            "breakdown": row.score_breakdown,
        }
        for row in rows
    ]
    exporters = {"csv": export_csv, "xlsx": export_xlsx, "pdf": export_pdf}
    media = {
        "csv": "text/csv",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "pdf": "application/pdf",
    }
    return Response(
        content=exporters[format](payload),
        media_type=media[format],
        headers={"Content-Disposition": f"attachment; filename=selection.{format}"},
    )
