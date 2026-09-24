from typing import Any

from app.rules.engine import evaluate


def score_candidate(
    candidate: dict[str, Any], config: dict[str, Any]
) -> dict[str, Any]:
    results = evaluate(config.get("filters", []), candidate)
    eligible = all(result.passed or result.severity != "BLOCKER" for result in results)
    score = 0.0
    components: list[dict[str, Any]] = []
    for criterion in config.get("weights", []):
        results_for_criterion = evaluate([criterion["rule"]], candidate)
        passed = results_for_criterion[0].passed
        points = float(criterion.get("weight", 0)) if passed else 0.0
        score += points
        components.append(
            {"id": criterion.get("id"), "passed": passed, "points": points}
        )
    return {
        "eligible": eligible,
        "score": score,
        "components": components,
        "results": [r.as_dict() for r in results],
    }


def select_candidates(
    candidates: list[dict[str, Any]], config: dict[str, Any]
) -> list[dict[str, Any]]:
    scored = [
        {**candidate, "selection": score_candidate(candidate, config)}
        for candidate in candidates
    ]
    eligible = [item for item in scored if item["selection"]["eligible"]]
    eligible.sort(
        key=lambda item: (
            -item["selection"]["score"],
            *(item.get(field, "") for field in config.get("tie_breakers", [])),
        )
    )
    quotas = config.get("quotas", [])
    selected: list[dict[str, Any]] = []
    for item in eligible:
        if all(
            sum(
                1 for chosen in selected if chosen.get(quota["field"]) == quota["value"]
            )
            < int(quota["limit"])
            or item.get(quota["field"]) != quota["value"]
            for quota in quotas
        ):
            selected.append(item)
    return selected
