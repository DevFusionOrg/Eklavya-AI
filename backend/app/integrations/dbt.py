"""DBT status adapter contracts and an offline deterministic implementation."""

from datetime import UTC, datetime

from app.integrations.base import StatusSync, StatusSyncRequest, StatusSyncResult


class MockDbtStatusSync:
    """In-memory DBT adapter for local development and acceptance tests.

    No network calls are made. Unknown references return ``PENDING`` so callers
    can exercise polling without accidentally treating missing data as paid.
    """

    def __init__(self, statuses: dict[str, str] | None = None) -> None:
        self.statuses = statuses or {}

    def get_status(self, request: StatusSyncRequest) -> StatusSyncResult:
        status = self.statuses.get(request.beneficiary_reference, "PENDING")
        return StatusSyncResult(
            application_reference=request.application_reference,
            beneficiary_reference=request.beneficiary_reference,
            status=status,
            provider_reference=(
                f"mock-dbt-{request.beneficiary_reference}"
                if status != "PENDING"
                else None
            ),
            as_of=datetime.now(UTC),
            message="Offline mock response; not a live DBT status.",
        )


def build_dbt_status_sync() -> StatusSync:
    """Build the explicitly offline DBT adapter.

    A live connector must be introduced separately with credential, signing,
    timeout, retry, and reconciliation policies reviewed by the deployment
    owner; this factory intentionally never contacts DBT.
    """

    return MockDbtStatusSync()
