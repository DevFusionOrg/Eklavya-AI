import hashlib
from datetime import timedelta

from minio import Minio

from app.core.config import settings

MAGIC_TYPES = {
    "application/pdf": (b"%PDF-",),
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
}


class DocumentValidationError(ValueError):
    pass


def detect_mime(content: bytes) -> str:
    for mime, signatures in MAGIC_TYPES.items():
        if any(content.startswith(signature) for signature in signatures):
            return mime
    raise DocumentValidationError("Unsupported document type; upload PDF, JPG, or PNG")


def validate_document(
    content: bytes,
    declared_mime: str | None,
    *,
    filename: str | None = None,
    max_size: int | None = None,
) -> tuple[str, str, int]:
    if len(content) > (max_size or settings.document_max_size_bytes):
        raise DocumentValidationError("Document exceeds the maximum allowed size")
    mime = detect_mime(content)
    if declared_mime and declared_mime != mime:
        raise DocumentValidationError("Declared MIME type does not match file content")
    if filename:
        suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        expected_suffixes = {
            "application/pdf": {"pdf"},
            "image/jpeg": {"jpg", "jpeg"},
            "image/png": {"png"},
        }
        if suffix not in expected_suffixes[mime]:
            raise DocumentValidationError("File extension does not match file content")
    return mime, hashlib.sha256(content).hexdigest(), len(content)


class MinioDocumentStorage:
    def __init__(self) -> None:
        self.client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )

    def put(self, content: bytes, object_key: str, mime: str) -> None:
        from io import BytesIO

        self.client.put_object(
            settings.minio_bucket,
            object_key,
            BytesIO(content),
            length=len(content),
            content_type=mime,
            metadata={"x-amz-server-side-encryption": "AES256"},
        )

    def delete(self, object_key: str) -> None:
        self.client.remove_object(settings.minio_bucket, object_key)

    def get(self, object_key: str) -> bytes:
        response = self.client.get_object(settings.minio_bucket, object_key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def presigned_get(self, object_key: str) -> str:
        return self.client.presigned_get_object(
            settings.minio_bucket,
            object_key,
            expires=timedelta(seconds=settings.document_url_expiry_seconds),
        )
