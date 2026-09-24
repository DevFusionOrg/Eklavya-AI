import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import settings

password_hasher = PasswordHasher()


def validate_password_policy(password: str) -> None:
    checks = (
        len(password) >= 12,
        any(char.isupper() for char in password),
        any(char.islower() for char in password),
        any(char.isdigit() for char in password),
        any(not char.isalnum() for char in password),
    )
    if not all(checks):
        raise ValueError(
            "Password must be at least 12 characters and include upper, lower, digit, and special character"
        )


def hash_password(password: str) -> str:
    validate_password_policy(password)
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bool(password_hasher.verify(password_hash, password))
    except (InvalidHashError, VerificationError, VerifyMismatchError):
        return False


def create_token(
    user_id: uuid.UUID,
    role: str,
    token_type: str,
    expires_delta: timedelta,
    version: int,
) -> str:
    now = datetime.now(UTC)
    claims: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "type": token_type,
        "jti": str(uuid.uuid4()),
        "ver": version,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str, expected_type: str) -> dict[str, Any]:
    claims = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    if claims.get("type") != expected_type or not claims.get("sub"):
        raise jwt.InvalidTokenError("Invalid token type")
    return claims
