"""External government-system adapter contracts and offline implementations."""

from app.integrations.base import (
    BeneficiaryExport,
    BeneficiaryExportResult,
    BeneficiaryRecord,
    DocumentFetch,
    DocumentFetchRequest,
    FetchedDocument,
    StatusSync,
    StatusSyncRequest,
    StatusSyncResult,
)
from app.integrations.dbt import MockDbtStatusSync
from app.integrations.digilocker import MockDigiLockerDocumentFetch
from app.integrations.pfms import MockPfmsBeneficiaryExport

__all__ = [
    "BeneficiaryExport",
    "BeneficiaryExportResult",
    "BeneficiaryRecord",
    "DocumentFetch",
    "DocumentFetchRequest",
    "FetchedDocument",
    "MockDbtStatusSync",
    "MockDigiLockerDocumentFetch",
    "MockPfmsBeneficiaryExport",
    "StatusSync",
    "StatusSyncRequest",
    "StatusSyncResult",
]
