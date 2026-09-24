import json
import re
import unicodedata
from datetime import UTC, date, datetime
from difflib import SequenceMatcher
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.applications.service import ApplicationService
from app.db.models import (
    Application,
    ApplicationDocument,
    Deficiency,
    ExtractedField,
    SchemeDocumentRequired,
    SchemeVersion,
)
from app.notifications.service import notify_deficiency, set_correction_deadline
from app.rules.engine import evaluate

DEFAULT_CONFIDENCE_THRESHOLD = 0.75
DEFAULT_NAME_MATCH_THRESHOLD = 0.82


def _message(en: str, hi: str) -> str:
    return json.dumps({"en": en, "hi": hi}, ensure_ascii=False)


def _normalized(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value)).casefold()
    return re.sub(r"[\W_]+", "", text, flags=re.UNICODE)


def fuzzy_matches(left: Any, right: Any, threshold: float) -> bool:
    left_normalized, right_normalized = _normalized(left), _normalized(right)
    if not left_normalized or not right_normalized:
        return False
    return SequenceMatcher(None, left_normalized, right_normalized).ratio() >= threshold


def _date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value).date()
        except ValueError:
            try:
                return date.fromisoformat(value)
            except ValueError:
                return None
    return None


def _config(version: SchemeVersion) -> dict[str, Any]:
    config = version.rules.get("validation", {})
    return config if isinstance(config, dict) else {}


async def validate_application(
    session: AsyncSession, application_id: Any
) -> list[Deficiency]:
    application = await session.scalar(
        select(Application).where(Application.id == application_id).with_for_update()
    )
    if application is None:
        return []
    version = await session.get(SchemeVersion, application.scheme_version_id)
    if version is None:
        return []
    documents = list(
        (
            await session.scalars(
                select(ApplicationDocument).where(
                    ApplicationDocument.application_id == application.id
                )
            )
        ).all()
    )
    required = list(
        (
            await session.scalars(
                select(SchemeDocumentRequired).where(
                    SchemeDocumentRequired.scheme_version_id == version.id
                )
            )
        ).all()
    )
    if any(document.ocr_status in {"PENDING", "PROCESSING"} for document in documents):
        return []

    existing = list(
        (
            await session.scalars(
                select(Deficiency).where(
                    Deficiency.application_id == application.id,
                    Deficiency.raised_by_type == "SYSTEM",
                    Deficiency.status == "OPEN",
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
    by_document: dict[Any, dict[str, ExtractedField]] = {}
    for field in fields:
        by_document.setdefault(field.document_id, {})[field.field] = field
    values = {field.field: field.value for field in fields}
    config = _config(version)
    threshold = float(config.get("confidence_threshold", DEFAULT_CONFIDENCE_THRESHOLD))
    deficiencies: list[Deficiency] = []
    existing_by_key = {
        (item.code, item.field, item.document_id): item for item in existing
    }
    active_keys: set[tuple[str, str | None, Any]] = set()

    def add(
        code: str,
        en: str,
        hi: str,
        severity: str,
        *,
        field: str | None = None,
        document_id: Any = None,
    ) -> None:
        key = (code, field, document_id)
        active_keys.add(key)
        deficiency = existing_by_key.get(key)
        if deficiency is None:
            deficiency = Deficiency(
                application_id=application.id,
                code=code,
                message=_message(en, hi),
                severity=severity,
                status="OPEN",
                raised_by_type="SYSTEM",
                field=field,
                document_id=document_id,
            )
            session.add(deficiency)
        else:
            deficiency.status = "OPEN"
            deficiency.resolved_at = None
        deficiencies.append(deficiency)

    for required_document in required:
        matching = next(
            (item for item in documents if item.doc_type == required_document.doc_type),
            None,
        )
        if matching is None:
            if required_document.is_mandatory:
                add(
                    "MISSING_DOCUMENT",
                    f"Required document missing: {required_document.label}",
                    f"आवश्यक दस्तावेज़ अनुपस्थित है: {required_document.label}",
                    "HIGH",
                    field=f"document:{required_document.doc_type}",
                )
            continue
        if matching.ocr_status == "FAILED":
            add(
                "OCR_FAILED",
                f"Document could not be read: {required_document.label}",
                f"दस्तावेज़ पढ़ा नहीं जा सका: {required_document.label}",
                "HIGH",
                document_id=matching.id,
            )
        expiry_field = by_document.get(matching.id, {}).get("expiry_date")
        expiry = _date(expiry_field.value) if expiry_field else None
        if expiry and expiry < datetime.now(UTC).date():
            add(
                "EXPIRED_DOCUMENT",
                f"Document has expired: {required_document.label}",
                f"दस्तावेज़ की वैधता समाप्त हो गई है: {required_document.label}",
                "HIGH",
                field="expiry_date",
                document_id=matching.id,
            )

    for field in fields:
        confidence = float(field.confidence or 0)
        if confidence < threshold:
            add(
                "LOW_CONFIDENCE",
                f"OCR field needs officer review: {field.field}",
                f"OCR फ़ील्ड की अधिकारी द्वारा जाँच आवश्यक है: {field.field}",
                "NEEDS_REVIEW",
                field=field.field,
                document_id=field.document_id,
            )

    match_threshold = float(
        config.get("name_match_threshold", DEFAULT_NAME_MATCH_THRESHOLD)
    )
    comparisons = config.get("comparisons", {})
    if not isinstance(comparisons, dict):
        comparisons = {}
    for extracted_field, form_field in comparisons.items():
        extracted = values.get(extracted_field)
        expected = application.form_data.get(form_field)
        if extracted is None or expected is None:
            continue
        threshold_value = float(
            config.get("comparison_thresholds", {}).get(
                extracted_field, match_threshold
            )
        )
        if not fuzzy_matches(extracted, expected, threshold_value):
            add(
                "FIELD_MISMATCH",
                f"{extracted_field} does not match the application",
                f"{extracted_field} आवेदन से मेल नहीं खाता है",
                "HIGH",
                field=extracted_field,
            )

    context = {
        "form_data": application.form_data,
        "extracted_fields": values,
    }
    rules = version.eligibility_rules or {}
    for result in evaluate(rules, context):
        if not result.passed:
            add(
                "ELIGIBILITY_RULE_FAILED",
                result.reason,
                result.reason,
                {
                    "BLOCKER": "CRITICAL",
                    "WARNING": "MEDIUM",
                    "NEEDS_REVIEW": "NEEDS_REVIEW",
                }.get(result.severity, "HIGH"),
            )

    for deficiency in existing:
        if (
            deficiency.code,
            deficiency.field,
            deficiency.document_id,
        ) not in active_keys:
            deficiency.status = "RESOLVED"
            deficiency.resolved_at = datetime.now(UTC)

    if deficiencies:
        await set_correction_deadline(application, config)
        await ApplicationService(session).transition(
            application,
            target="DEFICIENT",
            actor_id=None,
            actor_role="SYSTEM",
            reason="Automated validation found deficiencies",
        )
        await notify_deficiency(
            session,
            application,
            f"Application requires correction. Open deficiencies: {len(deficiencies)}.",
        )
    else:
        application.correction_deadline = None
        await ApplicationService(session).transition(
            application,
            target="UNDER_SCRUTINY",
            actor_id=None,
            actor_role="SYSTEM",
            reason="Automated validation passed",
        )
    return deficiencies
