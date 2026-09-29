"""PFMS beneficiary export adapter contracts and offline implementation."""

import re
from datetime import UTC, datetime

from app.integrations.base import (
    BeneficiaryExport,
    BeneficiaryExportResult,
    BeneficiaryRecord,
)


class MockPfmsBeneficiaryExport:
    """Validate and retain PFMS batches locally without submitting them."""

    def __init__(self) -> None:
        self.batches: dict[str, list[BeneficiaryRecord]] = {}

    def export(
        self, records: list[BeneficiaryRecord], batch_reference: str
    ) -> BeneficiaryExportResult:
        if not re.fullmatch(r"[A-Za-z0-9_-]{3,80}", batch_reference):
            raise ValueError("batch_reference must contain 3-80 safe characters")
        if not records:
            raise ValueError("at least one beneficiary record is required")
        if batch_reference in self.batches:
            raise ValueError("batch_reference has already been exported")
        for record in records:
            if record.amount_paise <= 0:
                raise ValueError("amount_paise must be positive")
            if not record.bank_account_token:
                raise ValueError("bank_account_token is required")
        self.batches[batch_reference] = list(records)
        return BeneficiaryExportResult(
            batch_reference=batch_reference,
            record_count=len(records),
            status="QUEUED_OFFLINE",
            submitted_at=datetime.now(UTC),
        )


def build_pfms_beneficiary_export() -> BeneficiaryExport:
    """Build the offline PFMS adapter; no PFMS submission is performed."""

    return MockPfmsBeneficiaryExport()
