"""Background worker process: `python -m app.worker`.

Runs the job scheduler only (never the HTTP API). Several replicas are safe: each job run
takes a PostgreSQL advisory lock.
"""

import asyncio
import signal

from app.core.clock import Clock
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.db.session import Database
from app.jobs.registry import JobContext
from app.jobs.scheduler import build_scheduler

logger = get_logger("app.worker")


async def run_worker() -> None:
    settings = get_settings()
    configure_logging(settings)
    database = Database.from_settings(settings)
    ctx = JobContext(session_factory=database.session_factory, clock=Clock(), settings=settings)
    scheduler = build_scheduler(ctx, database.engine)

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)

    scheduler.start()
    logger.info("worker_started", jobs=[job.id for job in scheduler.get_jobs()])
    try:
        await stop.wait()
    finally:
        scheduler.shutdown(wait=False)
        await database.dispose()
        logger.info("worker_stopped")


if __name__ == "__main__":
    asyncio.run(run_worker())
