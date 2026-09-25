import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_roles
from app.db.models import Scheme, SchemeDocumentRequired, SchemeVersion, User
from app.db.session import get_db_session

router = APIRouter(prefix="/schemes", tags=["schemes"])


class SchemeCreate(BaseModel):
    code: str = Field(min_length=2, max_length=64, pattern=r"^[A-Z0-9_-]+$")
    name: str = Field(min_length=2, max_length=255)
    description: str | None = None


class SchemeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = None
    is_active: bool | None = None


class DocumentDefinition(BaseModel):
    doc_type: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=255)
    mandatory: bool = True
    validity_rules: dict[str, Any] = Field(default_factory=dict)


class VersionCreate(BaseModel):
    form_schema: dict[str, Any] = Field(default_factory=dict)
    ui_hints: dict[str, Any] = Field(default_factory=dict)
    eligibility_rules: dict[str, Any] = Field(default_factory=dict)
    selection_rules: dict[str, Any] = Field(default_factory=dict)
    rules: dict[str, Any] = Field(default_factory=dict)
    documents: list[DocumentDefinition] = Field(default_factory=list)
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    open_at: datetime | None = None
    close_at: datetime | None = None

    @model_validator(mode="after")
    def dates_are_ordered(self) -> "VersionCreate":
        if self.open_at and self.close_at and self.close_at <= self.open_at:
            raise ValueError("close_at must be after open_at")
        return self


class VersionUpdate(BaseModel):
    form_schema: dict[str, Any] | None = None
    ui_hints: dict[str, Any] | None = None
    eligibility_rules: dict[str, Any] | None = None
    selection_rules: dict[str, Any] | None = None
    rules: dict[str, Any] | None = None
    effective_to: datetime | None = None
    open_at: datetime | None = None
    close_at: datetime | None = None


class SchemeResponse(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    description: str | None
    is_active: bool

    model_config = {"from_attributes": True}


class VersionResponse(BaseModel):
    id: uuid.UUID
    scheme_id: uuid.UUID
    version_number: int
    status: str
    form_schema: dict[str, Any]
    ui_hints: dict[str, Any]
    eligibility_rules: dict[str, Any]
    selection_rules: dict[str, Any]
    effective_from: datetime
    effective_to: datetime | None
    open_at: datetime | None
    close_at: datetime | None
    published_at: datetime | None

    model_config = {"from_attributes": True}


async def get_scheme_or_404(scheme_id: uuid.UUID, session: AsyncSession) -> Scheme:
    scheme = await session.get(Scheme, scheme_id)
    if scheme is None:
        raise HTTPException(status_code=404, detail="Scheme not found")
    return scheme


@router.get("", response_model=list[SchemeResponse])
async def list_schemes(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[Scheme]:
    return list((await session.scalars(select(Scheme).order_by(Scheme.name))).all())


@router.post("", response_model=SchemeResponse, status_code=status.HTTP_201_CREATED)
async def create_scheme(
    payload: SchemeCreate,
    _: Annotated[User, Depends(require_roles("ADMIN"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Scheme:
    existing = await session.scalar(select(Scheme).where(Scheme.code == payload.code))
    if existing:
        raise HTTPException(status_code=409, detail="Scheme code already exists")
    scheme = Scheme(**payload.model_dump())
    session.add(scheme)
    await session.commit()
    await session.refresh(scheme)
    return scheme


@router.patch("/{scheme_id}", response_model=SchemeResponse)
async def update_scheme(
    scheme_id: uuid.UUID,
    payload: SchemeUpdate,
    _: Annotated[User, Depends(require_roles("ADMIN"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Scheme:
    scheme = await get_scheme_or_404(scheme_id, session)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(scheme, field, value)
    await session.commit()
    await session.refresh(scheme)
    return scheme


@router.delete("/{scheme_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_scheme(
    scheme_id: uuid.UUID,
    _: Annotated[User, Depends(require_roles("ADMIN"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    scheme = await get_scheme_or_404(scheme_id, session)
    scheme.is_active = False
    await session.commit()


@router.post(
    "/{scheme_id}/versions",
    response_model=VersionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_version(
    scheme_id: uuid.UUID,
    payload: VersionCreate,
    _: Annotated[User, Depends(require_roles("ADMIN"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SchemeVersion:
    await get_scheme_or_404(scheme_id, session)
    latest = await session.scalar(
        select(SchemeVersion)
        .where(SchemeVersion.scheme_id == scheme_id)
        .order_by(SchemeVersion.version_number.desc())
    )
    version = SchemeVersion(
        scheme_id=scheme_id,
        version_number=(latest.version_number + 1 if latest else 1),
        effective_from=payload.effective_from or datetime.now(UTC),
        **payload.model_dump(exclude={"documents", "effective_from", "effective_to"}),
        effective_to=payload.effective_to,
    )
    session.add(version)
    await session.flush()
    for document in payload.documents:
        session.add(
            SchemeDocumentRequired(
                scheme_version_id=version.id,
                doc_type=document.doc_type,
                label=document.label,
                is_mandatory=document.mandatory,
                validity_rules=document.validity_rules,
            )
        )
    await session.commit()
    await session.refresh(version)
    return version


@router.get("/{scheme_id}/versions", response_model=list[VersionResponse])
async def list_versions(
    scheme_id: uuid.UUID,
    _: Annotated[User, Depends(require_roles("ADMIN"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[SchemeVersion]:
    await get_scheme_or_404(scheme_id, session)
    return list(
        (
            await session.scalars(
                select(SchemeVersion)
                .where(SchemeVersion.scheme_id == scheme_id)
                .order_by(SchemeVersion.version_number.desc())
            )
        ).all()
    )


@router.post(
    "/{scheme_id}/versions/{version_id}/publish", response_model=VersionResponse
)
async def publish_version(
    scheme_id: uuid.UUID,
    version_id: uuid.UUID,
    _: Annotated[User, Depends(require_roles("ADMIN"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SchemeVersion:
    version = await session.scalar(
        select(SchemeVersion).where(
            SchemeVersion.id == version_id, SchemeVersion.scheme_id == scheme_id
        )
    )
    if version is None:
        raise HTTPException(status_code=404, detail="Scheme version not found")
    if version.status == "PUBLISHED":
        return version
    if version.status == "RETIRED":
        raise HTTPException(
            status_code=409, detail="Retired version cannot be published"
        )
    published = await session.scalars(
        select(SchemeVersion).where(
            SchemeVersion.scheme_id == scheme_id,
            SchemeVersion.status == "PUBLISHED",
        )
    )
    for previous in published:
        previous.status = "RETIRED"
        previous.effective_to = version.effective_from
    version.status = "PUBLISHED"
    version.published_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(version)
    return version


@router.patch("/{scheme_id}/versions/{version_id}", response_model=VersionResponse)
async def update_version(
    scheme_id: uuid.UUID,
    version_id: uuid.UUID,
    payload: VersionUpdate,
    _: Annotated[User, Depends(require_roles("ADMIN"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SchemeVersion:
    version = await session.scalar(
        select(SchemeVersion).where(
            SchemeVersion.id == version_id, SchemeVersion.scheme_id == scheme_id
        )
    )
    if version is None:
        raise HTTPException(status_code=404, detail="Scheme version not found")
    if version.status != "DRAFT":
        raise HTTPException(
            status_code=409, detail="Published and retired versions are immutable"
        )
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(version, field, value)
    await session.commit()
    await session.refresh(version)
    return version


@router.get("/{code}/form-schema")
async def applicant_form_schema(
    code: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    scheme = await session.scalar(
        select(Scheme).where(Scheme.code == code, Scheme.is_active.is_(True))
    )
    if scheme is None:
        raise HTTPException(status_code=404, detail="Active scheme not found")
    version = await session.scalar(
        select(SchemeVersion)
        .where(
            SchemeVersion.scheme_id == scheme.id,
            SchemeVersion.status == "PUBLISHED",
        )
        .order_by(SchemeVersion.version_number.desc())
    )
    if version is None:
        raise HTTPException(status_code=404, detail="No published scheme version")
    documents = list(
        (
            await session.scalars(
                select(SchemeDocumentRequired).where(
                    SchemeDocumentRequired.scheme_version_id == version.id
                )
            )
        ).all()
    )
    return {
        "scheme": {"code": scheme.code, "name": scheme.name},
        "version_id": str(version.id),
        "version_number": version.version_number,
        "form_schema": version.form_schema,
        "ui_hints": version.ui_hints,
        "documents": [
            {
                "doc_type": document.doc_type,
                "label": document.label,
                "mandatory": document.is_mandatory,
                "validity_rules": document.validity_rules,
            }
            for document in documents
        ],
    }
