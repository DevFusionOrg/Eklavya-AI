import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.applications.service import ApplicationService
from app.audit.service import AuditService
from app.auth.dependencies import require_roles
from app.core.errors import DomainError
from app.db.models import (
    Applicant,
    Application,
    ApplicationDocument,
    Award,
    FollowupRequirement,
    FollowupSubmission,
    SchemeVersion,
    User,
)
from app.db.session import get_db_session

router = APIRouter(prefix="/followups", tags=["followups"])


class Instalment(BaseModel):
    label: str = Field(min_length=1, max_length=100)
    amount: Decimal = Field(ge=0)
    due_date: datetime | None = None


class AwardCreate(BaseModel):
    application_id: uuid.UUID
    amount: Decimal = Field(ge=0)
    instalments: list[Instalment] = Field(default_factory=list)
    requirements: list[dict[str, Any]] | None = None


class SubmissionCreate(BaseModel):
    data: dict[str, Any] = Field(default_factory=dict)
    document_id: uuid.UUID | None = None


class ReviewSubmission(BaseModel):
    status: Literal["ACCEPTED", "REJECTED"]
    remarks: str = Field(min_length=2, max_length=2000)


async def _owned_award(award_id: uuid.UUID, user: User, session: AsyncSession) -> Award:
    applicant = await session.scalar(
        select(Applicant).where(Applicant.user_id == user.id)
    )
    award = await session.scalar(
        select(Award)
        .join(Application, Application.id == Award.application_id)
        .where(
            Award.id == award_id,
            Application.applicant_id == getattr(applicant, "id", None),
        )
    )
    if award is None:
        raise HTTPException(status_code=404, detail="Award not found")
    return award


def _configured_requirements(
    version: SchemeVersion, award: Award, requested: list[dict[str, Any]] | None
) -> list[FollowupRequirement]:
    definitions = requested
    if definitions is None:
        definitions = version.rules.get("followup_requirements", [])
    requirements = []
    for definition in definitions:
        due_date = definition.get("due_date")
        if due_date is None:
            due_date = datetime.now(UTC) + timedelta(
                days=int(definition.get("due_days", 30))
            )
        elif isinstance(due_date, str):
            due_date = datetime.fromisoformat(due_date)
        requirements.append(
            FollowupRequirement(
                award_id=award.id,
                name=str(definition["name"]),
                requirement_type=str(definition.get("type", "DOCUMENT")),
                validation_schema=definition.get("validation_schema", {}),
                due_date=due_date,
            )
        )
    return requirements


@router.post("/awards", status_code=status.HTTP_201_CREATED)
async def create_award(
    payload: AwardCreate,
    user: Annotated[User, Depends(require_roles("ADMIN"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    application = await session.get(
        Application, payload.application_id, with_for_update=True
    )
    if application is None or application.status != "APPROVED":
        raise DomainError(
            "APPLICATION_NOT_APPROVED", "Only approved applications can be awarded", 409
        )
    existing = await session.scalar(
        select(Award).where(Award.application_id == application.id)
    )
    if existing:
        raise DomainError(
            "AWARD_EXISTS", "An award already exists for this application", 409
        )
    version = await session.get(SchemeVersion, application.scheme_version_id)
    if version is None:
        raise DomainError("SCHEME_VERSION_NOT_FOUND", "Scheme version not found", 409)
    award = Award(
        application_id=application.id,
        amount=payload.amount,
        instalments=[item.model_dump(mode="json") for item in payload.instalments],
        status="PLANNED",
        awarded_at=datetime.now(UTC),
    )
    session.add(award)
    await session.flush()
    session.add_all(_configured_requirements(version, award, payload.requirements))
    await ApplicationService(session).transition(
        application,
        target="AWARDED",
        actor_id=user.id,
        actor_role=user.role,
        reason="Award created",
    )
    await AuditService(session).append(
        actor_id=user.id,
        actor_role=user.role,
        action="AWARD_CREATED",
        entity_type="AWARD",
        entity_id=award.id,
        after={"application_id": str(application.id), "amount": str(payload.amount)},
    )
    await session.commit()
    return {
        "id": str(award.id),
        "application_id": str(award.application_id),
        "status": award.status,
    }


@router.get("/mine")
async def list_my_awards(
    user: Annotated[User, Depends(require_roles("APPLICANT"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[dict[str, Any]]:
    applicant = await session.scalar(
        select(Applicant).where(Applicant.user_id == user.id)
    )
    if applicant is None:
        return []
    rows = list(
        (
            await session.execute(
                select(Award, FollowupRequirement)
                .join(Application, Application.id == Award.application_id)
                .outerjoin(
                    FollowupRequirement, FollowupRequirement.award_id == Award.id
                )
                .where(Application.applicant_id == applicant.id)
                .order_by(FollowupRequirement.due_date.asc())
            )
        ).all()
    )
    grouped: dict[uuid.UUID, dict[str, Any]] = {}
    for award, requirement in rows:
        item = grouped.setdefault(
            award.id,
            {
                "id": str(award.id),
                "amount": str(award.amount),
                "instalments": award.instalments,
                "status": award.status,
                "requirements": [],
            },
        )
        if requirement:
            item["requirements"].append(
                {
                    "id": str(requirement.id),
                    "name": requirement.name,
                    "type": requirement.requirement_type,
                    "due_date": requirement.due_date,
                    "status": requirement.status,
                }
            )
    return list(grouped.values())


@router.post("/{requirement_id}/submissions")
async def submit_followup(
    requirement_id: uuid.UUID,
    payload: SubmissionCreate,
    user: Annotated[User, Depends(require_roles("APPLICANT"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    requirement = await session.scalar(
        select(FollowupRequirement)
        .join(Award, Award.id == FollowupRequirement.award_id)
        .join(Application, Application.id == Award.application_id)
        .join(Applicant, Applicant.id == Application.applicant_id)
        .where(FollowupRequirement.id == requirement_id, Applicant.user_id == user.id)
    )
    if requirement is None:
        raise HTTPException(status_code=404, detail="Requirement not found")
    if requirement.status == "ACCEPTED":
        raise DomainError(
            "REQUIREMENT_ALREADY_ACCEPTED", "This requirement is already accepted", 409
        )
    if payload.document_id:
        document = await session.scalar(
            select(ApplicationDocument)
            .join(Application, Application.id == ApplicationDocument.application_id)
            .join(Award, Award.application_id == Application.id)
            .where(
                ApplicationDocument.id == payload.document_id,
                Award.id == requirement.award_id,
            )
        )
        if document is None:
            raise HTTPException(
                status_code=422, detail="Document is not attached to this award"
            )
    submission = FollowupSubmission(
        requirement_id=requirement.id,
        submitted_by=user.id,
        data=payload.data,
        document_id=payload.document_id,
    )
    session.add(submission)
    requirement.status = "SUBMITTED"
    await AuditService(session).append(
        actor_id=user.id,
        actor_role=user.role,
        action="FOLLOWUP_SUBMITTED",
        entity_type="FOLLOWUP_REQUIREMENT",
        entity_id=requirement.id,
        after={"submission_id": str(submission.id)},
    )
    await session.commit()
    return {
        "id": str(submission.id),
        "requirement_id": str(requirement.id),
        "status": submission.status,
    }


@router.get("/review")
async def review_followups(
    _: Annotated[
        User, Depends(require_roles("SCRUTINY_OFFICER", "VERIFYING_OFFICER", "ADMIN"))
    ],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[dict[str, Any]]:
    rows = list(
        (
            await session.execute(
                select(FollowupSubmission, FollowupRequirement, Award, Application)
                .join(
                    FollowupRequirement,
                    FollowupRequirement.id == FollowupSubmission.requirement_id,
                )
                .join(Award, Award.id == FollowupRequirement.award_id)
                .join(Application, Application.id == Award.application_id)
                .where(FollowupSubmission.status == "SUBMITTED")
                .order_by(FollowupSubmission.created_at.asc())
            )
        ).all()
    )
    return [
        {
            "id": str(submission.id),
            "requirement_id": str(requirement.id),
            "requirement": requirement.name,
            "application_id": str(application.id),
            "award_id": str(award.id),
            "data": submission.data,
            "document_id": (
                str(submission.document_id) if submission.document_id else None
            ),
        }
        for submission, requirement, award, application in rows
    ]


@router.post("/submissions/{submission_id}/review")
async def review_followup(
    submission_id: uuid.UUID,
    payload: ReviewSubmission,
    user: Annotated[
        User, Depends(require_roles("SCRUTINY_OFFICER", "VERIFYING_OFFICER", "ADMIN"))
    ],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    submission = await session.get(FollowupSubmission, submission_id)
    if submission is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    requirement = await session.get(FollowupRequirement, submission.requirement_id)
    if requirement is None:
        raise HTTPException(status_code=404, detail="Requirement not found")
    submission.status = payload.status
    submission.reviewed_by = user.id
    submission.reviewed_at = datetime.now(UTC)
    submission.review_remarks = payload.remarks
    requirement.status = payload.status
    award = await session.get(Award, requirement.award_id)
    if award and payload.status == "ACCEPTED":
        open_requirements = await session.scalar(
            select(FollowupRequirement.id).where(
                FollowupRequirement.award_id == award.id,
                FollowupRequirement.status.in_(("OVERDUE",)),
            )
        )
        if open_requirements is None and award.status == "ON_HOLD":
            award.status = "PLANNED"
            award.hold_reason = None
    await AuditService(session).append(
        actor_id=user.id,
        actor_role=user.role,
        action=f"FOLLOWUP_{payload.status}",
        entity_type="FOLLOWUP_SUBMISSION",
        entity_id=submission.id,
        after={"remarks": payload.remarks},
        reason=payload.remarks,
    )
    await session.commit()
    return {"id": str(submission.id), "status": submission.status}
