from typing import Any, cast

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class DomainError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def error_payload(code: str, message: str, details: Any = None) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "details": details}}


async def domain_error_handler(_: Request, exc: Exception) -> JSONResponse:
    error = cast(DomainError, exc)
    return JSONResponse(
        status_code=error.status_code,
        content=error_payload(error.code, error.message),
    )


async def http_error_handler(_: Request, exc: Exception) -> JSONResponse:
    error = cast(StarletteHTTPException, exc)
    return JSONResponse(
        status_code=error.status_code,
        content=error_payload("HTTP_ERROR", str(error.detail)),
    )


async def validation_error_handler(_: Request, exc: Exception) -> JSONResponse:
    error = cast(RequestValidationError, exc)
    return JSONResponse(
        status_code=422,
        content=error_payload(
            "VALIDATION_ERROR", "Request validation failed", error.errors()
        ),
    )
