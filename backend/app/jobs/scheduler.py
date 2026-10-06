"""APScheduler wiring: every registered job runs on its trigger through `run_job`."""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import AsyncEngine

from app.jobs.registry import JOBS, JobContext
from app.jobs.runner import run_job

MISFIRE_GRACE_SECONDS = 300


def build_scheduler(ctx: JobContext, lock_engine: AsyncEngine) -> AsyncIOScheduler:
    import app.jobs.tasks  # noqa: F401 - registers the jobs

    scheduler = AsyncIOScheduler(timezone="UTC")
    for definition in JOBS.values():
        scheduler.add_job(
            run_job,
            kwargs={"definition": definition, "ctx": ctx, "lock_engine": lock_engine},
            id=definition.name,
            name=definition.description,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=MISFIRE_GRACE_SECONDS,
            **definition.trigger,
        )
    return scheduler
