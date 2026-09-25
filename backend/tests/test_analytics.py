from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from app.analytics import confidence_buckets, stage_durations, state_from_form_data


def test_stage_durations_uses_completed_status_intervals() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    history = [
        SimpleNamespace(to_status="SUBMITTED", created_at=start),
        SimpleNamespace(
            to_status="UNDER_SCRUTINY", created_at=start + timedelta(days=2)
        ),
        SimpleNamespace(
            to_status="OFFICER_VERIFIED", created_at=start + timedelta(days=5)
        ),
    ]
    assert stage_durations(history) == {
        "SUBMITTED": 2.0,
        "UNDER_SCRUTINY": 3.0,
    }


def test_confidence_buckets_and_state_fallbacks() -> None:
    assert confidence_buckets([0.2, 0.75, 0.89, 0.9, 1.0]) == {
        "LOW": 1,
        "MEDIUM": 2,
        "HIGH": 2,
    }
    assert state_from_form_data({"state": "Odisha"}) == "Odisha"
    assert state_from_form_data({"address": {"state": "Jharkhand"}}) == "Jharkhand"
    assert state_from_form_data({}) == "UNKNOWN"
