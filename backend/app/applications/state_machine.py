from dataclasses import dataclass

from app.core.errors import DomainError

STATUSES = (
    "DRAFT",
    "SUBMITTED",
    "AUTO_VALIDATION",
    "DEFICIENT",
    "RESUBMITTED",
    "UNDER_SCRUTINY",
    "OFFICER_VERIFIED",
    "SELECTED",
    "NOT_SELECTED",
    "WAITLISTED",
    "APPROVED",
    "AWARDED",
    "CLOSED",
)


@dataclass(frozen=True)
class Transition:
    source: str
    target: str
    roles: frozenset[str]


TRANSITIONS = (
    Transition("DRAFT", "SUBMITTED", frozenset({"APPLICANT"})),
    Transition("SUBMITTED", "AUTO_VALIDATION", frozenset({"SYSTEM"})),
    Transition(
        "AUTO_VALIDATION", "DEFICIENT", frozenset({"SYSTEM", "SCRUTINY_OFFICER"})
    ),
    Transition(
        "AUTO_VALIDATION", "UNDER_SCRUTINY", frozenset({"SYSTEM", "SCRUTINY_OFFICER"})
    ),
    Transition("DEFICIENT", "RESUBMITTED", frozenset({"APPLICANT"})),
    Transition(
        "RESUBMITTED", "UNDER_SCRUTINY", frozenset({"SYSTEM", "SCRUTINY_OFFICER"})
    ),
    Transition("UNDER_SCRUTINY", "OFFICER_VERIFIED", frozenset({"VERIFYING_OFFICER"})),
    Transition("OFFICER_VERIFIED", "SELECTED", frozenset({"COMMITTEE_MEMBER"})),
    Transition("OFFICER_VERIFIED", "NOT_SELECTED", frozenset({"COMMITTEE_MEMBER"})),
    Transition("OFFICER_VERIFIED", "WAITLISTED", frozenset({"COMMITTEE_MEMBER"})),
    Transition("SELECTED", "APPROVED", frozenset({"ADMIN"})),
    Transition("APPROVED", "AWARDED", frozenset({"ADMIN"})),
    Transition("AWARDED", "CLOSED", frozenset({"ADMIN"})),
    Transition("DRAFT", "CLOSED", frozenset({"APPLICANT"})),
    Transition("SUBMITTED", "CLOSED", frozenset({"APPLICANT"})),
    Transition("DEFICIENT", "CLOSED", frozenset({"APPLICANT"})),
)


def legal_transition(source: str, target: str, role: str) -> bool:
    return any(
        transition.source == source
        and transition.target == target
        and (
            role in transition.roles
            or "SYSTEM" in transition.roles
            and role == "SYSTEM"
        )
        for transition in TRANSITIONS
    )


def assert_transition(source: str, target: str, role: str) -> None:
    if not legal_transition(source, target, role):
        raise DomainError(
            "ILLEGAL_APPLICATION_TRANSITION",
            f"{role} cannot transition application from {source} to {target}",
            status_code=409,
        )
