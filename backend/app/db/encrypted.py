"""SQLAlchemy type for encrypted sensitive string columns."""

from typing import Any

from sqlalchemy import String
from sqlalchemy.types import TypeDecorator

from app.core.encryption import decrypt_value, encrypt_value


class EncryptedString(TypeDecorator[str]):
    impl = String
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect: Any) -> str | None:
        return encrypt_value(value) if value is not None else None

    def process_result_value(self, value: str | None, dialect: Any) -> str | None:
        return decrypt_value(value) if value is not None else None
