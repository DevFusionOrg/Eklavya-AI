import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import decode_token
from app.core.config import settings
from app.db.models import User
from app.db.session import get_db_session

bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )
    try:
        claims = decode_token(credentials.credentials, "access")
        user_id = uuid.UUID(claims["sub"])
    except (ValueError, KeyError, jwt.PyJWTError) as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        ) from error
    user = await session.scalar(select(User).where(User.id == user_id))
    if user is None or not user.is_active or user.token_version != claims.get("ver"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user"
        )
    if user.locked_until and user.locked_until > datetime.now(UTC):
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="Account locked")
    return user


def require_roles(*roles: str) -> Callable[..., Awaitable[User]]:
    async def role_dependency(
        user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role"
            )
        return user

    return role_dependency


async def revoke_token(jti: str, expires_at: int) -> None:
    client = Redis.from_url(settings.redis_url)
    try:
        ttl = max(expires_at - int(datetime.now(UTC).timestamp()), 1)
        await client.setex(f"auth:revoked:{jti}", ttl, "1")
    finally:
        await client.aclose()


async def is_token_revoked(jti: str) -> bool:
    client = Redis.from_url(settings.redis_url)
    try:
        return bool(await client.exists(f"auth:revoked:{jti}"))
    finally:
        await client.aclose()
