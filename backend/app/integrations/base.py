"""Stable contracts shared by DBT, PFMS, and DigiLocker adapters.

These contracts deliberately contain domain identifiers rather than provider
credentials or provider-specific response objects. Production connectors can
implement them without leaking external API details into application services.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class StatusSyncRequest:
    """Request the latest payment status for one beneficiary reference."""

    application_reference: str
    beneficiary_reference: str


@dataclass(frozen=True)
class StatusSyncResult:
    """Normalized status returned by a DBT status connector."""

    application_reference: str
    beneficiary_reference: str
    status: str
    provider_reference: str | None
    as_of: datetime
    message: str | None = None


class StatusSync(Protocol):
    """Read payment/disbursement status from a DBT provider."""

    def get_status(self, request: StatusSyncRequest) -> StatusSyncResult:
        """Return a normalized, non-authoritative provider status."""


@dataclass(frozen=True)
class BeneficiaryRecord:
    """Minimum PFMS export record; sensitive values are already tokenized."""

    application_reference: str
    beneficiary_reference: str
    name: str
    bank_account_token: str
    amount_paise: int
    purpose_code: str


@dataclass(frozen=True)
class BeneficiaryExportResult:
    """Receipt for a provider export submission."""

    batch_reference: str
    record_count: int
    status: str
    submitted_at: datetime


class BeneficiaryExport(Protocol):
    """Submit approved beneficiary records to a PFMS connector."""

    def export(
        self, records: list[BeneficiaryRecord], batch_reference: str
    ) -> BeneficiaryExportResult:
        """Submit a batch and return a provider-neutral receipt."""


@dataclass(frozen=True)
class DocumentFetchRequest:
    """Reference used to retrieve a consented DigiLocker document."""

    user_reference: str
    document_uri: str
    consent_reference: str


@dataclass(frozen=True)
class FetchedDocument:
    """Normalized document bytes and metadata returned by a document connector."""

    document_uri: str
    content: bytes
    media_type: str
    filename: str
    checksum_sha256: str
    issued_at: datetime | None


class DocumentFetch(Protocol):
    """Fetch a document only after the caller has recorded consent."""

    def fetch(self, request: DocumentFetchRequest) -> FetchedDocument:
        """Fetch one document from the configured document provider."""
