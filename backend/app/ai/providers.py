import json
from dataclasses import dataclass
from typing import Any, Protocol, cast

import httpx

from app.ai.schemas import Recommendation


class LlmProvider(Protocol):
    @property
    def model(self) -> str: ...

    def complete(self, prompt: str) -> dict[str, Any]:
        """Return one JSON object matching the recommendation schema."""


@dataclass(frozen=True)
class MockProvider:
    model: str = "rules-only"

    def complete(self, prompt: str) -> dict[str, Any]:
        payload = json.loads(prompt)
        risks = payload.get("risks", [])
        evidence = payload.get("evidence", [])
        needs_review = bool(risks)
        return Recommendation.model_validate(
            {
                "summary": (
                    "Rules-only review found risks requiring human review."
                    if needs_review
                    else "Rules-only review found no automated blocking risks."
                ),
                "criterion_assessments": [
                    {
                        "criterion": "automated_validation",
                        "result": "NEEDS_REVIEW" if needs_review else "PASS",
                        "rationale": "Derived from deterministic validation results.",
                        "evidence": evidence[:5],
                    }
                ],
                "flagged_risks": risks,
                "cited_evidence": evidence[:10],
                "suggested_action": "REQUEST_REVIEW" if needs_review else "PROCEED",
                "confidence": 0.5 if needs_review else 0.8,
            }
        ).model_dump()


@dataclass
class HttpJsonProvider:
    model: str
    endpoint: str
    api_key: str = ""

    def complete(self, prompt: str) -> dict[str, Any]:
        response = httpx.post(
            self.endpoint,
            headers={"Authorization": "Bearer " + self.api_key} if self.api_key else {},
            json={
                "model": self.model,
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=30,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return cast(dict[str, Any], json.loads(content))


def build_provider(name: str, model: str) -> LlmProvider:
    normalized = name.casefold()
    if normalized in {"mock", "local"}:
        return MockProvider(model=model)
    if normalized == "openai":
        from app.core.config import settings

        return HttpJsonProvider(
            model=model,
            endpoint="https://api.openai.com/v1/chat/completions",
            api_key=settings.ai_api_key,
        )
    if normalized == "anthropic":
        from app.core.config import settings

        return HttpJsonProvider(
            model=model,
            endpoint="https://api.anthropic.com/v1/messages",
            api_key=settings.ai_api_key,
        )
    raise ValueError(f"Unsupported AI provider: {name}")
