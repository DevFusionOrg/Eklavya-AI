from datetime import timedelta
from uuid import uuid4

import jwt
import pytest

from app.auth.security import (
    create_token,
    decode_token,
    hash_password,
    validate_password_policy,
    verify_password,
)


def test_argon2_password_hash_round_trip() -> None:
    password = "StrongPassword9!"
    password_hash = hash_password(password)
    assert password_hash.startswith("$argon2")
    assert verify_password(password, password_hash)
    assert not verify_password("WrongPassword9!", password_hash)


def test_password_policy_rejects_weak_password() -> None:
    with pytest.raises(ValueError):
        validate_password_policy("password")


def test_expired_access_token_is_rejected() -> None:
    token = create_token(uuid4(), "APPLICANT", "access", timedelta(seconds=-1), 0)
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_token(token, "access")


def test_token_type_is_enforced() -> None:
    token = create_token(uuid4(), "APPLICANT", "refresh", timedelta(minutes=5), 0)
    with pytest.raises(jwt.InvalidTokenError):
        decode_token(token, "access")
