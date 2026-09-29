"""HTTP security controls applied to every API response."""

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import settings


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.extend(
                    [
                        (b"x-content-type-options", b"nosniff"),
                        (b"x-frame-options", b"DENY"),
                        (b"referrer-policy", b"no-referrer"),
                        (
                            b"permissions-policy",
                            b"camera=(), microphone=(), geolocation=()",
                        ),
                        (
                            b"content-security-policy",
                            b"default-src 'none'; frame-ancestors 'none'",
                        ),
                    ]
                )
                if settings.environment.lower() not in {"development", "test"}:
                    headers.append(
                        (
                            b"strict-transport-security",
                            b"max-age=31536000; includeSubDomains",
                        )
                    )
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_headers)


class RequestSizeAndCsrfMiddleware:
    """Reject oversized requests and protect a future cookie-auth API.

    Current authentication is Authorization bearer tokens, so normal requests
    do not need CSRF tokens. If an auth session cookie is introduced, unsafe
    requests must include a matching X-CSRF-Token header.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            content_length = headers.get(b"content-length")
            if content_length:
                try:
                    too_large = int(content_length) > settings.max_request_body_bytes
                except ValueError:
                    too_large = True
                if too_large:
                    await self._reject(send, 413, b"Request body too large")
                    return
            method = scope.get("method", "GET").upper()
            if method in {"POST", "PUT", "PATCH", "DELETE"}:
                cookies = headers.get(b"cookie", b"").decode("latin-1")
                if "eklavya_session=" in cookies:
                    csrf = headers.get(b"x-csrf-token")
                    if not csrf:
                        await self._reject(send, 403, b"CSRF token required")
                        return
        await self.app(scope, receive, send)

    @staticmethod
    async def _reject(send: Send, status: int, body: bytes) -> None:
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [(b"content-type", b"text/plain; charset=utf-8")],
            }
        )
        await send({"type": "http.response.body", "body": body})
