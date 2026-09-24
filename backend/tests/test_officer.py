from app.api.v1.officer import OfficerAction
from app.applications.state_machine import legal_transition


def test_verification_signoff_is_reserved_for_verifying_role_by_default() -> None:
    assert legal_transition("UNDER_SCRUTINY", "OFFICER_VERIFIED", "VERIFYING_OFFICER")
    assert not legal_transition(
        "UNDER_SCRUTINY", "OFFICER_VERIFIED", "SCRUTINY_OFFICER"
    )


def test_rejection_requires_structured_reason_fields() -> None:
    action = OfficerAction(
        action="REJECT",
        reason_code="INELIGIBLE",
        remarks="Income exceeds scheme ceiling",
    )
    assert action.reason_code == "INELIGIBLE"
    assert action.remarks


def test_override_source_is_explicit() -> None:
    action = OfficerAction(
        action="VERIFY",
        override_source="AI",
        remarks="Evidence was reviewed manually",
    )
    assert action.override_source == "AI"
