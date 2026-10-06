"""Background jobs: registry, runner (locks, failures) and job functions."""

import uuid
from datetime import timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

import app.jobs.tasks  # noqa: F401 - registers the jobs
from app.core.clock import FixedClock
from app.core.config import Settings
from app.jobs.registry import JOBS, JobContext, JobDefinition
from app.jobs.runner import JobOutcome, advisory_lock, run_job
from app.modules.auth.models import RefreshToken, UserSession
from tests.helpers import AuthenticatedUser, login


@pytest.fixture
def ctx(
    session_factory: async_sessionmaker[AsyncSession], clock: FixedClock, settings: Settings
) -> JobContext:
    return JobContext(session_factory=session_factory, clock=clock, settings=settings)


def test_registered_jobs() -> None:
    assert {"generate_alerts", "cleanup_expired_tokens"} <= set(JOBS)
    assert JOBS["cleanup_expired_tokens"].trigger == {"trigger": "cron", "hour": 3, "minute": 0}


async def test_runner_isolates_failures(ctx: JobContext) -> None:
    async def boom(_ctx: JobContext) -> None:
        raise RuntimeError("boom")

    failing = JobDefinition("boom", boom, "fails", {"trigger": "interval", "hours": 1})
    assert await run_job(failing, ctx) is JobOutcome.FAILED


async def test_runner_skips_when_lock_is_held(ctx: JobContext, engine: AsyncEngine) -> None:
    calls: list[str] = []

    async def record(_ctx: JobContext) -> dict[str, int]:
        calls.append("ran")
        return {"items": 1}

    definition = JobDefinition("locked", record, "test", {"trigger": "interval", "hours": 1})
    async with advisory_lock(engine, "job:locked") as acquired:
        assert acquired
        assert await run_job(definition, ctx, engine) is JobOutcome.SKIPPED
    assert await run_job(definition, ctx, engine) is JobOutcome.SUCCEEDED
    assert calls == ["ran"]


async def test_cleanup_expired_tokens(
    client: AsyncClient,
    user: AuthenticatedUser,
    ctx: JobContext,
    clock: FixedClock,
    db_session: AsyncSession,
) -> None:
    await login(client, user.email)
    await client.post("/api/v1/auth/logout", headers=user.headers)

    async def count(model: type[RefreshToken] | type[UserSession]) -> int:
        stmt = select(func.count()).select_from(model)
        if model is UserSession:
            stmt = stmt.where(UserSession.user_id == uuid.UUID(user.id))
        return int(await db_session.scalar(stmt) or 0)

    assert await count(UserSession) == 2
    clock.set(clock.now() + timedelta(days=61))
    result = await JOBS["cleanup_expired_tokens"].function(ctx)
    assert result is not None and result["sessions"] >= 2
    assert await count(UserSession) == 0
    assert await count(RefreshToken) == 0
