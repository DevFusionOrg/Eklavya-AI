import json
from pathlib import Path

from app.ai.providers import MockProvider


def main() -> None:
    cases = json.loads((Path(__file__).parent / "cases.json").read_text())
    provider = MockProvider()
    agreed = 0
    for case in cases:
        output = provider.complete(
            json.dumps(
                {
                    "risks": (
                        [{"code": "LABELLED_RISK", "description": "fixture"}]
                        if case["risk"]
                        else []
                    ),
                    "evidence": [],
                }
            )
        )
        agreed += output["suggested_action"] == case["human"]
    print(f"cases={len(cases)} agreement_rate={agreed / len(cases):.3f}")


if __name__ == "__main__":
    main()
