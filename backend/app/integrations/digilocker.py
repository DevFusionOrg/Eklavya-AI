"""DigiLocker document-fetch contract and consent-aware offline mock."""

import hashlib
from datetime import datetime

from app.integrations.base import (
    DocumentFetch,
    DocumentFetchRequest,
    FetchedDocument,
)


class MockDigiLockerDocumentFetch:
    """Return fixtures registered by tests after checking the consent reference."""

    def __init__(
        self,
        documents: dict[str, tuple[bytes, str, str, datetime | None]] | None = None,
    ) -> None:
        self.documents = documents or {}

    def fetch(self, request: DocumentFetchRequest) -> FetchedDocument:
        if not request.consent_reference.strip():
            raise ValueError("consent_reference is required")
        try:
            content, media_type, filename, issued_at = self.documents[
                request.document_uri
            ]
        except KeyError as error:
            raise LookupError(
                "document is not available in the offline fixture"
            ) from error
        return FetchedDocument(
            document_uri=request.document_uri,
            content=content,
            media_type=media_type,
            filename=filename,
            checksum_sha256=hashlib.sha256(content).hexdigest(),
            issued_at=issued_at,
        )


def build_digilocker_document_fetch() -> DocumentFetch:
    """Build an empty offline DigiLocker adapter.

    Real DigiLocker access requires an approved integration/onboarding process,
    client credentials, redirect/callback handling, consent artefacts, token
    storage and rotation, document URI validation, and production security
    review. None of those credentials or network calls are configured here.
    """

    return MockDigiLockerDocumentFetch()
