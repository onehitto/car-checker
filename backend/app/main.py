"""Application factory.

Run with: `uvicorn app.main:create_app --factory`
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health
from app.api.openapi import API_DESCRIPTION, OPENAPI_TAGS
from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.core.error_handlers import register_error_handlers
from app.core.logging import configure_logging, get_logger
from app.core.middleware import (
    REQUEST_ID_HEADER,
    BodySizeLimitMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
)
from app.core.rate_limit import RateLimitMiddleware, build_rate_limiter, parse_rate
from app.core.security import configure_password_hashing
from app.db.session import Database
from app.modules.attachments.storage import build_storage
from app.modules.notifications.email import build_email_sender

logger = get_logger(__name__)

DOCS_PATHS = ("/docs", "/docs/oauth2-redirect", "/redoc")
MULTIPART_OVERHEAD = 1024 * 1024  # form fields and boundaries around an uploaded file


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings)
    configure_password_hashing(
        time_cost=settings.password_hash_time_cost,
        memory_cost=settings.password_hash_memory_cost,
        parallelism=settings.password_hash_parallelism,
    )

    database = Database.from_settings(settings)
    rate_limiter = build_rate_limiter(settings)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        logger.info("application_startup", environment=settings.app_env.value)
        yield
        await rate_limiter.close()
        await database.dispose()
        logger.info("application_shutdown")

    docs = settings.docs_enabled
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=API_DESCRIPTION,
        docs_url="/docs" if docs else None,
        redoc_url="/redoc" if docs else None,
        openapi_url="/openapi.json" if docs else None,
        openapi_tags=OPENAPI_TAGS,
        swagger_ui_parameters={"persistAuthorization": True, "displayRequestDuration": True},
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.db = database
    app.state.rate_limiter = rate_limiter
    app.state.email_sender = build_email_sender(settings)
    app.state.storage = build_storage(settings)

    # Middleware added last runs first:
    # request context -> security headers -> CORS -> rate limit -> body size limit.
    app.add_middleware(
        BodySizeLimitMiddleware, max_bytes=settings.max_upload_size + MULTIPART_OVERHEAD
    )
    if settings.rate_limit_enabled:
        app.add_middleware(
            RateLimitMiddleware,
            limiter=rate_limiter,
            rate=parse_rate(settings.rate_limit_default),
            exempt_paths=("/health", f"{settings.api_v1_prefix}/health"),
        )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,  # bearer tokens, no cookies
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept-Language", REQUEST_ID_HEADER],
        expose_headers=[REQUEST_ID_HEADER, "Retry-After", "Content-Disposition"],
        max_age=600,
    )
    app.add_middleware(
        SecurityHeadersMiddleware, hsts=settings.is_production, docs_paths=DOCS_PATHS
    )
    app.add_middleware(RequestContextMiddleware)

    register_error_handlers(app)

    app.include_router(health.router)  # unversioned /health for load balancers
    app.include_router(api_router, prefix=settings.api_v1_prefix)
    return app
