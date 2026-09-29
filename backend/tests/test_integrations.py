from datetime import UTC, datetime

import pytest

from app.integrations import (
    BeneficiaryRecord,
    DocumentFetchRequest,
    MockDbtStatusSync,
    MockDigiLockerDocumentFetch,
    MockPfmsBeneficiaryExport,
    StatusSyncRequest,
)


def test_dbt_mock_defaults_unknown_reference_to_pending() -> None:
    result = MockDbtStatusSync().get_status(StatusSyncRequest("APP-1", "BEN-1"))
    assert result.status == "PENDING"
    assert result.provider_reference is None
    assert "not a live" in (result.message or "")


def test_pfms_mock_validates_and_is_idempotency_safe() -> None:
    adapter = MockPfmsBeneficiaryExport()
    record = BeneficiaryRecord(
        "APP-1", "BEN-1", "Asha", "acct-token", 12500, "SCHOLARSHIP"
    )
    result = adapter.export([record], "batch-2026-01")
    assert result.status == "QUEUED_OFFLINE"
    assert result.record_count == 1
    with pytest.raises(ValueError, match="already"):
        adapter.export([record], "batch-2026-01")


def test_pfms_mock_rejects_empty_and_non_positive_records() -> None:
    adapter = MockPfmsBeneficiaryExport()
    with pytest.raises(ValueError, match="at least one"):
        adapter.export([], "batch-1")
    record = BeneficiaryRecord("APP-1", "BEN-1", "Asha", "acct-token", 0, "SCHOLARSHIP")
    with pytest.raises(ValueError, match="positive"):
        adapter.export([record], "batch-1")


def test_digilocker_mock_requires_consent_and_returns_checksum() -> None:
    issued_at = datetime(2026, 1, 1, tzinfo=UTC)
    adapter = MockDigiLockerDocumentFetch(
        {"uri:1": (b"pdf-fixture", "application/pdf", "certificate.pdf", issued_at)}
    )
    request = DocumentFetchRequest("user-1", "uri:1", "consent-1")
    document = adapter.fetch(request)
    assert document.content == b"pdf-fixture"
    assert document.checksum_sha256
    with pytest.raises(ValueError, match="consent"):
        adapter.fetch(DocumentFetchRequest("user-1", "uri:1", ""))
    with pytest.raises(LookupError):
        adapter.fetch(DocumentFetchRequest("user-1", "missing", "consent-1"))
