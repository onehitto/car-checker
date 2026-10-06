"""Run a job once: advisory lock, timing, structured logging, failure isolation."""

import hashlib
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from enum import StrEnum

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.logging import get_logger
from app.jobs.registry import JobContext, JobDefinition

logger = get_logger("app.jobs")


class JobOutcome(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


def lock_key(name: str) -> int:
    """Stable signed 64-bit key for pg_advisory_lock."""
    return int.from_bytes(hashlib.sha256(name.encode()).digest()[:8], "big", signed=True)


@asynccontextmanager
async def advisory_lock(engine: AsyncEngine, name: str) -> AsyncIterator[bool]:
    """Try to take a PostgreSQL session-level advisory lock; yields whether it was acquired.

    Several worker replicas can therefore run the scheduler without executing a job twice.
    """
    key = lock_key(name)
    async with engine.connect() as connection:
        acquired = bool(
            await connection.scalar(text("SELECT pg_try_advisory_lock(:k)"), {"k": key})
        )
        try:
            yield acquired
        finally:
            if acquired:
                await connection.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": key})
            await connection.commit()


async def run_job(
    definition: JobDefinition, ctx: JobContext, lock_engine: AsyncEngine | None = None
) -> JobOutcome:
    """Never raises: a failing job is logged and the scheduler keeps running."""
    log = logger.bind(job=definition.name)
    started = time.perf_counter()
    try:
        if lock_engine is None:
            result = await definition.function(ctx)
        else:
            async with advisory_lock(lock_engine, f"job:{definition.name}") as acquired:
                if not acquired:
                    log.info("job_skipped", reason="already running elsewhere")
                    return JobOutcome.SKIPPED
                result = await definition.function(ctx)
    except Exception:
        log.exception("job_failed", duration_ms=_elapsed_ms(started))
        return JobOutcome.FAILED
    log.info("job_succeeded", duration_ms=_elapsed_ms(started), **(result or {}))
    return JobOutcome.SUCCEEDED


def _elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 2)
