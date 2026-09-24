import logging
import uuid
from typing import cast

import jwt
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.audit.service import AuditService
from app.auth.security import decode_token
from app.db.session import async_session_factory

logger = logging.getLogger(__name__)


class MutationAuditMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("method") not in {
            "POST",
            "PUT",
            "PATCH",
            "DELETE",
        }:
            await self.app(scope, receive, send)
            return

        status_code = 500

        async def capture_status(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = cast(int, message["status"])
            await send(message)

        await self.app(scope, receive, capture_status)
        request_id = scope.get("request_id")
        headers = dict(scope.get("headers", []))
        actor_id = None
        actor_role = None
        authorization = headers.get(b"authorization", b"").decode()
        if authorization.lower().startswith("bearer "):
            try:
                claims = decode_token(authorization[7:], "access")
                actor_id = uuid.UUID(claims["sub"])
                actor_role = claims.get("role")
            except (ValueError, KeyError, jwt.PyJWTError):
                logger.info("audit_actor_unavailable", extra={"request_id": request_id})
        async with async_session_factory() as session:
            try:
                await AuditService(session).append(
                    actor_id=actor_id,
                    actor_role=actor_role,
                    action=f"{scope['method']} {scope['path']} [{status_code}]",
                    entity_type="HTTP_REQUEST",
                    entity_id=uuid.uuid5(uuid.NAMESPACE_URL, str(request_id)),
                    request_id=str(request_id) if request_id else None,
                    ip=scope.get("client", ("unknown", 0))[0],
                )
                await session.commit()
            except Exception:
                await session.rollback()
                logger.exception(
                    "audit_append_failed", extra={"request_id": request_id}
                )
