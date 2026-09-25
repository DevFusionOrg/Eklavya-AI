import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.ai import router as ai_router
from app.api.v1.applications import router as applications_router
from app.api.v1.audit import router as audit_router
from app.api.v1.auth import router as auth_router
from app.api.v1.documents import router as documents_router
from app.api.v1.followups import router as followups_router
from app.api.v1.health import router as health_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.officer import router as officer_router
from app.api.v1.rules import router as rules_router
from app.api.v1.schemes import router as schemes_router
from app.api.v1.selection import router as selection_router
from app.audit.middleware import MutationAuditMiddleware
from app.core.config import settings
from app.core.errors import (
    DomainError,
    domain_error_handler,
    http_error_handler,
    validation_error_handler,
)
from app.core.logging import RequestIdMiddleware, configure_logging


def create_app() -> FastAPI:
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        from app.db.session import engine

        await engine.dispose()

    application = FastAPI(
        title=settings.app_name, version=settings.app_version, lifespan=lifespan
    )
    application.add_middleware(RequestIdMiddleware)
    application.add_middleware(MutationAuditMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.add_exception_handler(DomainError, domain_error_handler)
    application.add_exception_handler(StarletteHTTPException, http_error_handler)
    application.add_exception_handler(RequestValidationError, validation_error_handler)
    application.include_router(health_router, prefix="/api/v1")
    application.include_router(health_router)
    application.include_router(officer_router, prefix="/api/v1")
    application.include_router(selection_router, prefix="/api/v1")
    application.include_router(auth_router, prefix="/api/v1")
    application.include_router(audit_router, prefix="/api/v1")
    application.include_router(ai_router, prefix="/api/v1")
    application.include_router(applications_router, prefix="/api/v1")
    application.include_router(schemes_router, prefix="/api/v1")
    application.include_router(rules_router, prefix="/api/v1")
    application.include_router(documents_router, prefix="/api/v1")
    application.include_router(followups_router, prefix="/api/v1")
    application.include_router(notifications_router, prefix="/api/v1")

    logging.getLogger(__name__).info("application_started")
    return application


app = create_app()
