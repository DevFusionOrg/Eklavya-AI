import asyncio
from collections.abc import Callable
from typing import Any

from sqlalchemy import delete, select

from app.core.config import settings
from app.db.models import ApplicationDocument, ExtractedField
from app.db.session import async_session_factory
from app.ocr.base import OcrEngine, build_ocr_engine
from app.ocr.extraction import classify_document, extract_fields
from app.storage.service import MinioDocumentStorage
from app.validation.service import validate_application
from app.worker import celery_app


def preprocess(content: bytes, mime: str) -> bytes:
    """Apply safe orientation, contrast, and denoising preprocessing to images."""
    if mime == "application/pdf":
        return content
    from io import BytesIO

    from PIL import Image, ImageEnhance, ImageFilter, ImageOps

    with Image.open(BytesIO(content)) as image:
        prepared = ImageOps.exif_transpose(image).convert("RGB")
        prepared = ImageEnhance.Contrast(prepared).enhance(1.15)
        prepared = prepared.filter(ImageFilter.MedianFilter(size=3))
        output = BytesIO()
        prepared.save(output, format="PNG")
        return output.getvalue()


async def _process(
    document_id: str,
    *,
    engine_factory: Callable[[], OcrEngine] = lambda: build_ocr_engine(
        settings.ocr_engine
    ),
    storage: MinioDocumentStorage | None = None,
) -> None:
    async with async_session_factory() as session:
        document = await session.scalar(
            select(ApplicationDocument)
            .where(ApplicationDocument.id == document_id)
            .with_for_update()
        )
        if document is None or document.ocr_status == "COMPLETED":
            return
        application_id = document.application_id
        document.ocr_status = "PROCESSING"
        await session.commit()
        content = (storage or MinioDocumentStorage()).get(document.object_key)
        boxes = engine_factory().extract_text_with_boxes(
            preprocess(content, document.mime), settings.ocr_languages
        )
        doc_type = classify_document(boxes, document.doc_type)
        document.doc_type = doc_type
        extracted = extract_fields(boxes, doc_type)
        await session.execute(
            delete(ExtractedField).where(ExtractedField.document_id == document.id)
        )
        for item in extracted:
            session.add(
                ExtractedField(
                    document_id=document.id,
                    field=item.field,
                    value=item.value,
                    confidence=item.confidence,
                    source_bbox=item.bbox,
                )
            )
        document.ocr_status = "COMPLETED"
        await session.commit()
        await _validate_if_ready(session, application_id)


async def _validate_if_ready(session: Any, application_id: Any) -> None:
    documents = list(
        (
            await session.scalars(
                select(ApplicationDocument).where(
                    ApplicationDocument.application_id == application_id
                )
            )
        ).all()
    )
    if documents and all(
        item.ocr_status in {"COMPLETED", "FAILED", "REVIEW_REQUIRED"}
        for item in documents
    ):
        from app.db.models import Application

        application = await session.scalar(
            select(Application)
            .where(Application.id == application_id)
            .with_for_update()
        )
        if application and application.status == "SUBMITTED":
            from app.applications.service import ApplicationService

            await ApplicationService(session).transition(
                application,
                target="AUTO_VALIDATION",
                actor_id=None,
                actor_role="SYSTEM",
                reason="All document OCR jobs completed",
            )
            await validate_application(session, application_id)
            await session.commit()


@celery_app.task(bind=True, max_retries=settings.ocr_task_max_retries)  # type: ignore[untyped-decorator]
def process_document(self: Any, document_id: str) -> None:
    try:
        asyncio.run(_process(document_id))
    except Exception as error:  # noqa: BLE001
        asyncio.run(_mark_failed(document_id))
        retry = self.retry
        retry(exc=error, countdown=2**self.request.retries)


async def _mark_failed(document_id: str) -> None:
    async with async_session_factory() as session:
        document = await session.scalar(
            select(ApplicationDocument).where(ApplicationDocument.id == document_id)
        )
        if document:
            application_id = document.application_id
            document.ocr_status = "FAILED"
            await session.commit()
            await _validate_if_ready(session, application_id)
