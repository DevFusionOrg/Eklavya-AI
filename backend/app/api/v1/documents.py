import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.applications.api_helpers import owned_application_for_user
from app.audit.service import AuditService
from app.auth.dependencies import get_current_user
from app.core.config import settings
from app.db.models import ApplicationDocument, Deficiency, User
from app.db.session import get_db_session
from app.storage.antivirus import NoOpAntivirus
from app.storage.quality import check_image_quality
from app.storage.service import (
    DocumentValidationError,
    MinioDocumentStorage,
    validate_document,
)

router = APIRouter(prefix="/applications", tags=["documents"])
scanner = NoOpAntivirus()


@router.post("/{application_id}/documents")
async def upload_document(
    application_id: uuid.UUID,
    doc_type: str,
    file: Annotated[UploadFile, File(...)],
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    application = await owned_application_for_user(application_id, user, session)
    if application.status not in {"DRAFT", "DEFICIENT"}:
        raise HTTPException(
            status_code=409, detail="Documents can only be attached to drafts"
        )
    if application.status == "DEFICIENT":
        flagged_types = {
            str(item).split(":", 1)[1]
            for item in (
                await session.scalars(
                    select(Deficiency.field).where(
                        Deficiency.application_id == application.id,
                        Deficiency.status == "OPEN",
                        Deficiency.field.like("document:%"),
                    )
                )
            ).all()
            if item and ":" in str(item)
        }
        flagged_documents = set(
            (
                await session.scalars(
                    select(Deficiency.document_id).where(
                        Deficiency.application_id == application.id,
                        Deficiency.status == "OPEN",
                        Deficiency.document_id.is_not(None),
                    )
                )
            ).all()
        )
        if not flagged_documents and doc_type not in flagged_types:
            raise HTTPException(
                status_code=422,
                detail="Only documents referenced by an open deficiency can be replaced",
            )
    max_size = settings.document_max_sizes.get(
        doc_type, settings.document_max_size_bytes
    )
    content = await file.read(max_size + 1)
    try:
        mime, checksum, size = validate_document(
            content,
            file.content_type,
            filename=file.filename,
            max_size=max_size,
        )
    except DocumentValidationError as error:
        raise HTTPException(status_code=415, detail=str(error)) from error
    if not await scanner.scan(content):
        raise HTTPException(
            status_code=422, detail="Document failed antivirus scanning"
        )
    quality = check_image_quality(content, mime)
    if not quality.passed:
        return {"accepted": False, "quality": quality.__dict__}
    duplicate = await session.scalar(
        select(ApplicationDocument).where(
            ApplicationDocument.application_id == application.id,
            ApplicationDocument.checksum == checksum,
        )
    )
    if duplicate:
        return {"accepted": True, "duplicate": True, "document_id": str(duplicate.id)}
    previous = await session.scalar(
        select(ApplicationDocument).where(
            ApplicationDocument.application_id == application.id,
            ApplicationDocument.doc_type == doc_type,
        )
    )
    object_key = f"applications/{application.id}/{uuid.uuid4()}"
    MinioDocumentStorage().put(content, object_key, mime)
    document = ApplicationDocument(
        application_id=application.id,
        object_key=object_key,
        doc_type=doc_type,
        checksum=checksum,
        size=size,
        mime=mime,
        ocr_status="PENDING",
    )
    session.add(document)
    await session.flush()
    if previous:
        MinioDocumentStorage().delete(previous.object_key)
        await session.delete(previous)
    await AuditService(session).append(
        actor_id=user.id,
        actor_role=user.role,
        action="DOCUMENT_UPLOADED",
        entity_type="APPLICATION_DOCUMENT",
        entity_id=document.id,
        after={"doc_type": doc_type, "checksum": checksum, "size": size},
    )
    await session.commit()
    from app.ocr.pipeline import process_document

    process_document.delay(str(document.id))
    return {
        "accepted": True,
        "document_id": str(document.id),
        "quality": quality.__dict__,
    }


@router.get("/{application_id}/documents/{document_id}/download")
async def download_document(
    application_id: uuid.UUID,
    document_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, str]:
    application = await owned_application_for_user(application_id, user, session)
    document = await session.scalar(
        select(ApplicationDocument).where(
            ApplicationDocument.id == document_id,
            ApplicationDocument.application_id == application.id,
        )
    )
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    url = MinioDocumentStorage().presigned_get(document.object_key)
    await AuditService(session).append(
        actor_id=user.id,
        actor_role=user.role,
        action="DOCUMENT_DOWNLOAD_URL_CREATED",
        entity_type="APPLICATION_DOCUMENT",
        entity_id=document.id,
        reason="Authorized document download",
    )
    await session.commit()
    return {"url": url, "expires_in": str(settings.document_url_expiry_seconds)}
