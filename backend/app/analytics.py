"""Pure aggregation helpers for analytics responses."""

from collections import Counter, defaultdict
from itertools import pairwise
from typing import Any


def stage_durations(history: list[Any]) -> dict[str, float]:
    durations: defaultdict[str, list[float]] = defaultdict(list)
    for current, following in pairwise(history):
        if current.to_status and following.created_at >= current.created_at:
            durations[current.to_status].append(
                (following.created_at - current.created_at).total_seconds() / 86400
            )
    return {
        stage: round(sum(values) / len(values), 2)
        for stage, values in durations.items()
        if values
    }


def confidence_buckets(values: list[float]) -> dict[str, int]:
    buckets = Counter(
        "LOW" if value < 0.75 else "MEDIUM" if value < 0.9 else "HIGH"
        for value in values
    )
    return {bucket: buckets.get(bucket, 0) for bucket in ("LOW", "MEDIUM", "HIGH")}


def state_from_form_data(form_data: dict[str, Any]) -> str:
    value = form_data.get("state")
    if value is None and isinstance(form_data.get("address"), dict):
        value = form_data["address"].get("state")
    return str(value).strip() if value else "UNKNOWN"
