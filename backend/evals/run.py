import argparse
import json
from pathlib import Path

from app.ai.providers import MockProvider


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
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
    metrics = {
        "cases": len(cases),
        "agreement_rate": round(agreed / len(cases), 3),
        "provider": provider.model,
    }
    print(json.dumps(metrics, sort_keys=True))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(metrics, indent=2) + "\n")


if __name__ == "__main__":
    main()
