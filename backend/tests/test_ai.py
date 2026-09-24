import json

import pytest

from app.ai.providers import MockProvider
from app.ai.schemas import EvidenceCitation, Recommendation
from app.ai.service import _validate_evidence
from app.core.errors import DomainError


def test_mock_provider_is_reproducible_and_rules_only() -> None:
    prompt = json.dumps({"risks": [], "evidence": []})
    provider = MockProvider()
    assert provider.complete(prompt) == provider.complete(prompt)
    assert provider.complete(prompt)["suggested_action"] == "PROCEED"


def test_hallucinated_evidence_is_rejected() -> None:
    recommendation = Recommendation(
        summary="test",
        criterion_assessments=[],
        flagged_risks=[],
        cited_evidence=[EvidenceCitation(field="missing", document_id="document-1")],
        suggested_action="REQUEST_REVIEW",
        confidence=0.2,
    )
    with pytest.raises(DomainError) as error:
        _validate_evidence(recommendation, {})
    assert error.value.code == "AI_INVALID_EVIDENCE"


def test_recommendation_schema_has_no_status_mutation_field() -> None:
    assert "status" not in Recommendation.model_fields
    assert "decision" not in Recommendation.model_fields
