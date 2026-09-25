import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field, field_validator
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import (
    is_token_revoked,
    require_roles,
    revoke_token,
)
from app.auth.security import (
    create_token,
    decode_token,
    hash_password,
    validate_password_policy,
    verify_password,
)
from app.core.config import settings
from app.db.models import User
from app.db.session import get_db_session

router = APIRouter(prefix="/auth", tags=["auth"])


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)

    @field_validator("password")
    @classmethod
    def password_policy(cls, value: str) -> str:
        validate_password_policy(value)
        return value


class OfficerCredentials(Credentials):
    role: str = Field(default="SCRUTINY_OFFICER", pattern="^(SCRUTINY_OFFICER|VERIFYING_OFFICER)$")


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


async def enforce_rate_limit(request: Request) -> None:
    client = Redis.from_url(settings.redis_url)
    key = f"auth:rate:{request.client.host if request.client else 'unknown'}"
    try:
        count = await client.incr(key)
        if count == 1:
            await client.expire(key, settings.auth_rate_window_seconds)
        if count > settings.auth_rate_limit:
            raise HTTPException(
                status_code=429, detail="Too many authentication attempts"
            )
    finally:
        await client.aclose()


def tokens_for(user: User) -> TokenResponse:
    access = create_token(
        user.id,
        user.role,
        "access",
        timedelta(minutes=settings.access_token_expire_minutes),
        user.token_version,
    )
    refresh = create_token(
        user.id,
        user.role,
        "refresh",
        timedelta(days=settings.refresh_token_expire_days),
        user.token_version,
    )
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    credentials: Credentials,
    _: Annotated[None, Depends(enforce_rate_limit)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TokenResponse:
    validate_password_policy(credentials.password)
    if await session.scalar(select(User).where(User.email == credentials.email)):
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(
        email=str(credentials.email).lower(),
        password_hash=hash_password(credentials.password),
        role="APPLICANT",
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return tokens_for(user)


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: Credentials,
    _: Annotated[None, Depends(enforce_rate_limit)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TokenResponse:
    user = await session.scalar(
        select(User).where(User.email == str(credentials.email).lower())
    )
    now = datetime.now(UTC)
    if user and user.locked_until and user.locked_until > now:
        raise HTTPException(status_code=423, detail="Account locked")
    if user is None or not verify_password(credentials.password, user.password_hash):
        if user:
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= settings.max_login_failures:
                user.locked_until = now + timedelta(minutes=settings.lockout_minutes)
            await session.commit()
        raise HTTPException(status_code=401, detail="Invalid credentials")
    user.failed_login_attempts = 0
    user.locked_until = None
    await session.commit()
    return tokens_for(user)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    payload: RefreshRequest,
    _: Annotated[None, Depends(enforce_rate_limit)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TokenResponse:
    try:
        claims = decode_token(payload.refresh_token, "refresh")
        if await is_token_revoked(claims["jti"]):
            raise jwt.InvalidTokenError("Revoked token")
        user = await session.scalar(
            select(User).where(User.id == uuid.UUID(claims["sub"]))
        )
    except (jwt.PyJWTError, ValueError, KeyError) as error:
        raise HTTPException(status_code=401, detail="Invalid refresh token") from error
    if user is None or not user.is_active or user.token_version != claims.get("ver"):
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    await revoke_token(claims["jti"], claims["exp"])
    return tokens_for(user)


@router.post("/logout", status_code=204)
async def logout(
    payload: RefreshRequest,
    _: Annotated[None, Depends(enforce_rate_limit)],
) -> None:
    try:
        claims = decode_token(payload.refresh_token, "refresh")
        await revoke_token(claims["jti"], claims["exp"])
    except (jwt.PyJWTError, KeyError) as error:
        raise HTTPException(status_code=401, detail="Invalid refresh token") from error


@router.post("/officers", response_model=dict[str, str], status_code=201)
async def create_officer(
    credentials: OfficerCredentials,
    _: Annotated[User, Depends(require_roles("ADMIN"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, str]:
    validate_password_policy(credentials.password)
    if await session.scalar(select(User).where(User.email == credentials.email)):
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(
        email=str(credentials.email).lower(),
        password_hash=hash_password(credentials.password),
        role=credentials.role,
    )
    session.add(user)
    await session.commit()
    return {"id": str(user.id), "role": user.role}


@router.get("/officers")
async def list_officers(
    _: Annotated[User, Depends(require_roles("ADMIN"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[dict[str, str | bool]]:
    users = list(
        (
            await session.scalars(
                select(User)
                .where(User.role.in_(("SCRUTINY_OFFICER", "VERIFYING_OFFICER")))
                .order_by(User.email)
            )
        ).all()
    )
    return [
        {"id": str(user.id), "email": user.email, "role": user.role, "is_active": user.is_active}
        for user in users
    ]
