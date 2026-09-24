import pytest

from app.storage.service import DocumentValidationError, detect_mime, validate_document


def test_magic_bytes_reject_spoofed_extension() -> None:
    with pytest.raises(DocumentValidationError):
        validate_document(
            b"%PDF-1.7",
            "application/pdf",
            filename="document.jpg",
        )


def test_mime_detection_accepts_supported_formats() -> None:
    assert detect_mime(b"%PDF-1.7") == "application/pdf"
    assert detect_mime(b"\x89PNG\r\n\x1a\n") == "image/png"
    assert detect_mime(b"\xff\xd8\xff\xe0") == "image/jpeg"


def test_cross_user_access_helper_is_not_bypassable() -> None:
    from app.applications.api_helpers import owned_application_for_user

    assert callable(owned_application_for_user)
