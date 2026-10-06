"""Health endpoints: API liveness + database connectivity. Exposes no server details."""

import asyncio
from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from app.api.deps import DbSession
from app.api.openapi import error_responses
from app.core.exceptions import ServiceUnavailableError
from app.core.logging import get_logger
from app.core.responses import ApiResponse, success

logger = get_logger(__name__)

router = APIRouter(tags=["Health"])

DATABASE_TIMEOUT_SECONDS = 2.0


class HealthStatus(BaseModel):
    status: Literal["ok"]
    database: Literal["ok"]


@router.get(
    "/health",
    response_model=ApiResponse[HealthStatus],
    summary="Health check",
    description="Returns 200 when the API and the database are reachable, 503 otherwise.",
    responses=error_responses(503),
)
async def health(session: DbSession) -> Any:
    try:
        await asyncio.wait_for(session.execute(text("SELECT 1")), DATABASE_TIMEOUT_SECONDS)
    except Exception as exc:  # noqa: BLE001 - any failure means "unhealthy"
        logger.error("health_check_failed", component="database", error=type(exc).__name__)
        raise ServiceUnavailableError("The database is unavailable.") from None
    return success({"status": "ok", "database": "ok"})
