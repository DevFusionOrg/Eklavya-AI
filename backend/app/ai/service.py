import hashlib
import json
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers import LlmProvider, build_provider
from app.ai.schemas import EvidenceCitation, Recommendation
from app.audit.service import AuditService
from app.core.config import settings
from app.core.errors import DomainError
from app.db.models import (
    AiRecommendation,
    Application,
    ApplicationDocument,
    Deficiency,
    ExtractedField,
)


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _safe_prompt_value(value: str | None) -> dict[str, Any]:
    if not value:
        return {"present": False}
    return {"present": True, "length": len(value), "last4": value[-4:]}


async def _context(
    session: AsyncSession, application: Application
) -> tuple[dict[str, Any], dict[tuple[str, str], EvidenceCitation]]:
    rows = list(
        (
            await session.execute(
                select(ExtractedField, ApplicationDocument)
                .join(
                    ApplicationDocument,
                    ApplicationDocument.id == ExtractedField.document_id,
                )
                .where(ApplicationDocument.application_id == application.id)
            )
        ).all()
    )
    evidence: dict[tuple[str, str], EvidenceCitation] = {}
    fields: list[dict[str, Any]] = []
    for field, document in rows:
        citation = EvidenceCitation(
            field=field.field,
            document_id=str(document.id),
            bbox=field.source_bbox,
        )
        evidence[(field.field, str(document.id))] = citation
        fields.append(
            {
                "field": field.field,
                "document_id": str(document.id),
                "value": _safe_prompt_value(field.value),
                "confidence": float(field.confidence or 0),
                "bbox": field.source_bbox,
            }
        )
    deficiencies = list(
        (
            await session.scalars(
                select(Deficiency).where(
                    Deficiency.application_id == application.id,
                    Deficiency.status == "OPEN",
                )
            )
        ).all()
    )
    risks = [
        {
            "code": item.code,
            "description": item.message,
            "evidence": (
                [
                    {
                        "field": item.field,
                        "document_id": str(item.document_id),
                        "bbox": None,
                    }
                ]
                if item.field and item.document_id
                else []
            ),
        }
        for item in deficiencies
    ]
    payload = {
        "application_status": application.status,
        "form_fields": sorted(application.form_data.keys()),
        "extracted_fields": fields,
        "risks": risks,
        "evidence": [item.model_dump() for item in evidence.values()],
    }
    return payload, evidence


def _validate_evidence(
    recommendation: Recommendation,
    evidence: dict[tuple[str, str], EvidenceCitation],
) -> Recommendation:
    citations = [
        *recommendation.cited_evidence,
        *[
            citation
            for assessment in recommendation.criterion_assessments
            for citation in assessment.evidence
        ],
        *[
            citation
            for risk in recommendation.flagged_risks
            for citation in risk.evidence
        ],
    ]
    for citation in citations:
        if (citation.field, citation.document_id) not in evidence:
            raise DomainError(
                "AI_INVALID_EVIDENCE",
                "AI recommendation cited an unavailable extracted field",
                502,
            )
    return recommendation


async def generate_recommendation(
    session: AsyncSession,
    application_id: uuid.UUID,
    *,
    provider: LlmProvider | None = None,
) -> Recommendation:
    application = await session.scalar(
        select(Application).where(Application.id == application_id)
    )
    if application is None:
        raise DomainError("APPLICATION_NOT_FOUND", "Application not found", 404)
    if application.status != "UNDER_SCRUTINY":
        raise DomainError(
            "APPLICATION_NOT_UNDER_SCRUTINY",
            "Recommendations are available only during officer scrutiny",
            409,
        )
    payload, evidence = await _context(session, application)
    prompt = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    selected = provider or build_provider(settings.ai_provider, settings.ai_model)
    raw: dict[str, Any] | None = None
    last_error: Exception | None = None
    for _ in range(settings.ai_max_retries + 1):
        try:
            raw = selected.complete(prompt)
            recommendation = Recommendation.model_validate(raw)
            recommendation = _validate_evidence(recommendation, evidence)
            break
        except (ValueError, TypeError, KeyError, DomainError) as error:
            last_error = error
    else:
        raise DomainError(
            "AI_OUTPUT_INVALID",
            "AI recommendation could not be validated safely",
            502,
        ) from last_error
    response_json = json.dumps(
        recommendation.model_dump(), sort_keys=True, separators=(",", ":")
    )
    row = AiRecommendation(
        application_id=application.id,
        model=selected.model,
        prompt_hash=_hash(prompt),
        response_hash=_hash(response_json),
        output=recommendation.model_dump(),
        confidence=recommendation.confidence,
    )
    session.add(row)
    await AuditService(session).append(
        actor_id=None,
        actor_role="SYSTEM",
        action="AI_RECOMMENDATION_CREATED",
        entity_type="APPLICATION",
        entity_id=application.id,
        after={"model": selected.model, "response_hash": row.response_hash},
        reason="Advisory verification assistant output",
    )
    await session.commit()
    return recommendation
