"""Job registry.

A job is a plain `async def job(ctx: JobContext) -> dict | None`. It knows nothing about the
scheduler, so the same functions can later be enqueued in a queue system (arq, Celery...).
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.clock import Clock
from app.core.config import Settings


@dataclass(frozen=True, slots=True)
class JobContext:
    session_factory: async_sessionmaker[AsyncSession]
    clock: Clock
    settings: Settings
    extras: dict[str, Any] = field(default_factory=dict)


JobResult = dict[str, Any] | None
JobFunction = Callable[[JobContext], Awaitable[JobResult]]


@dataclass(frozen=True, slots=True)
class JobDefinition:
    name: str
    function: JobFunction
    description: str
    trigger: dict[str, Any]  # APScheduler trigger arguments, e.g. {"trigger": "cron", "hour": 3}


JOBS: dict[str, JobDefinition] = {}


def job(name: str, *, description: str, **trigger: Any) -> Callable[[JobFunction], JobFunction]:
    """Register a job with its schedule."""

    def register(function: JobFunction) -> JobFunction:
        if name in JOBS:
            raise ValueError(f"Job '{name}' is already registered")
        JOBS[name] = JobDefinition(name, function, description, trigger)
        return function

    return register
