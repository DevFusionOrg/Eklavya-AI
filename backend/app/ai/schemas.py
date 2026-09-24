from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class EvidenceCitation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: str
    document_id: str
    bbox: dict[str, float] | None = None


class CriterionAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    criterion: str
    result: Literal["PASS", "FAIL", "NEEDS_REVIEW"]
    rationale: str
    evidence: list[EvidenceCitation] = Field(default_factory=list)


class FlaggedRisk(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    description: str
    evidence: list[EvidenceCitation] = Field(default_factory=list)


class Recommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str
    criterion_assessments: list[CriterionAssessment]
    flagged_risks: list[FlaggedRisk]
    cited_evidence: list[EvidenceCitation]
    suggested_action: Literal["PROCEED", "REQUEST_REVIEW", "REQUEST_CORRECTION"]
    confidence: float = Field(ge=0, le=1)
