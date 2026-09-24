from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.applications.service import ApplicationService
from app.applications.state_machine import assert_transition, legal_transition
from app.core.errors import DomainError
from app.db.models import Application


@pytest.mark.parametrize(
    ("source", "target", "role"),
    [
        ("DRAFT", "SUBMITTED", "APPLICANT"),
        ("SUBMITTED", "AUTO_VALIDATION", "SYSTEM"),
        ("AUTO_VALIDATION", "DEFICIENT", "SYSTEM"),
        ("AUTO_VALIDATION", "UNDER_SCRUTINY", "SCRUTINY_OFFICER"),
        ("DEFICIENT", "RESUBMITTED", "APPLICANT"),
        ("RESUBMITTED", "UNDER_SCRUTINY", "SCRUTINY_OFFICER"),
        ("UNDER_SCRUTINY", "OFFICER_VERIFIED", "VERIFYING_OFFICER"),
        ("OFFICER_VERIFIED", "SELECTED", "COMMITTEE_MEMBER"),
        ("OFFICER_VERIFIED", "NOT_SELECTED", "COMMITTEE_MEMBER"),
        ("OFFICER_VERIFIED", "WAITLISTED", "COMMITTEE_MEMBER"),
        ("SELECTED", "APPROVED", "ADMIN"),
        ("APPROVED", "AWARDED", "ADMIN"),
        ("AWARDED", "CLOSED", "ADMIN"),
    ],
)
def test_legal_transitions(source: str, target: str, role: str) -> None:
    assert legal_transition(source, target, role)
    assert_transition(source, target, role)


@pytest.mark.parametrize(
    ("source", "target", "role"),
    [
        ("DRAFT", "AWARDED", "APPLICANT"),
        ("SUBMITTED", "APPROVED", "ADMIN"),
        ("AUTO_VALIDATION", "SELECTED", "COMMITTEE_MEMBER"),
        ("UNDER_SCRUTINY", "SELECTED", "COMMITTEE_MEMBER"),
        ("SELECTED", "CLOSED", "APPLICANT"),
        ("CLOSED", "DRAFT", "ADMIN"),
        ("DRAFT", "SUBMITTED", "ADMIN"),
    ],
)
def test_illegal_transitions_raise_domain_error(
    source: str, target: str, role: str
) -> None:
    with pytest.raises(DomainError) as error:
        assert_transition(source, target, role)
    assert error.value.code == "ILLEGAL_APPLICATION_TRANSITION"


@pytest.mark.asyncio
async def test_repeated_submit_is_idempotent() -> None:
    application = Application(
        id=uuid4(),
        applicant_id=uuid4(),
        scheme_version_id=uuid4(),
        status="SUBMITTED",
        form_data={},
    )
    session = AsyncMock()
    result = await ApplicationService(session).transition(
        application,
        target="SUBMITTED",
        actor_id=uuid4(),
        actor_role="APPLICANT",
    )
    assert result is application
    session.add.assert_not_called()
