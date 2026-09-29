"""Application-level authenticated encryption for sensitive database fields."""

import base64
import hashlib
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings


def _key() -> bytes:
    return hashlib.sha256(settings.field_encryption_key.encode("utf-8")).digest()


def encrypt_value(value: str) -> str:
    nonce = os.urandom(12)
    ciphertext = AESGCM(_key()).encrypt(nonce, value.encode("utf-8"), None)
    return base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")


def decrypt_value(value: str) -> str:
    raw = base64.urlsafe_b64decode(value.encode("ascii"))
    if len(raw) < 13:
        raise ValueError("encrypted value is truncated")
    return AESGCM(_key()).decrypt(raw[:12], raw[12:], None).decode("utf-8")
