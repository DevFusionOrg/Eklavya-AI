import json
import logging
import re
import sys
from typing import Any

from starlette.types import ASGIApp, Message, Receive, Scope, Send

_PII_KEY = re.compile(
    r"(aadhaar|password|token|secret|email|phone|mobile|access_key|authorization)",
    re.IGNORECASE,
)


def scrub_pii(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if _PII_KEY.search(str(key)) else scrub_pii(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [scrub_pii(item) for item in value]
    if isinstance(value, str):
        return re.sub(r"\b\d{12}\b", "[REDACTED]", value)
    return value


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        return json.dumps(scrub_pii(payload), default=str)


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())


class RequestIdMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = next(
            (
                value.decode()
                for key, value in scope.get("headers", [])
                if key.lower() == b"x-request-id"
            ),
            None,
        )
        if not request_id:
            import uuid

            request_id = str(uuid.uuid4())

        async def send_with_request_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode()))
                message["headers"] = headers
            await send(message)

        scope["request_id"] = request_id
        await self.app(scope, receive, send_with_request_id)
