import asyncio
from typing import Any

import httpx
from fastapi import APIRouter
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.db.session import engine

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


async def check_database() -> bool:
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError:
        return False


async def check_redis() -> bool:
    client = Redis.from_url(settings.redis_url)
    try:
        return bool(await client.ping())
    except RedisError:
        return False
    finally:
        await client.aclose()


async def check_minio() -> bool:
    try:
        async with httpx.AsyncClient(timeout=2) as client:
            response = await client.get(f"{settings.minio_url}/minio/health/live")
        return response.is_success
    except httpx.HTTPError:
        return False


@router.get("/ready")
async def ready() -> dict[str, Any]:
    database, redis, minio = await asyncio.gather(
        check_database(), check_redis(), check_minio()
    )
    dependencies = {"database": database, "redis": redis, "minio": minio}
    return {
        "status": "ready" if all(dependencies.values()) else "not_ready",
        "dependencies": dependencies,
    }
