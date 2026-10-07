"""Management commands.

python -m app.cli seed            # upsert reference data (system catalogs)
"""

import argparse
import asyncio
import sys
import time
from collections.abc import Callable, Coroutine, Sequence
from typing import Any

from app.core.clock import Clock
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.core.security import configure_password_hashing
from app.db.demo import DEMO_EMAIL, DEMO_PASSWORD, DemoSeeder
from app.db.seeds import seed_reference_data
from app.db.session import Database
from app.jobs.registry import JOBS, JobContext
from app.jobs.runner import JobOutcome, run_job

logger = get_logger("app.cli")


async def _wait_db(args: argparse.Namespace) -> int:
    database = Database.from_settings(get_settings())
    deadline = time.monotonic() + args.timeout
    try:
        while True:
            try:
                await database.ping()
            except Exception as exc:  # noqa: BLE001 - any failure means "not ready yet"
                if time.monotonic() >= deadline:
                    logger.error("database_unreachable", error=type(exc).__name__)
                    return 1
                await asyncio.sleep(1)
            else:
                logger.info("database_ready")
                return 0
    finally:
        await database.dispose()


async def _seed(args: argparse.Namespace) -> int:
    settings = get_settings()
    if args.demo and settings.is_production:
        sys.stderr.write("Demo data is never created in production.\n")
        return 2
    configure_password_hashing(
        time_cost=settings.password_hash_time_cost,
        memory_cost=settings.password_hash_memory_cost,
        parallelism=settings.password_hash_parallelism,
    )
    database = Database.from_settings(settings)
    try:
        async with database.session_factory() as session:
            counts = await seed_reference_data(session)
            await session.commit()
            logger.info("seed_completed", **counts)
            if args.demo:
                created = await DemoSeeder(session, settings, Clock()).run()
                sys.stdout.write(
                    f"Demo account: {DEMO_EMAIL} / {DEMO_PASSWORD}\n"
                    if created
                    else f"Demo account {DEMO_EMAIL} already exists.\n"
                )
    finally:
        await database.dispose()
    return 0


async def _list_jobs(_args: argparse.Namespace) -> int:
    import app.jobs.tasks  # noqa: F401 - registers the jobs

    for definition in JOBS.values():
        trigger = ", ".join(f"{key}={value}" for key, value in definition.trigger.items())
        sys.stdout.write(f"{definition.name:<28} {trigger:<40} {definition.description}\n")
    return 0


async def _run_job(args: argparse.Namespace) -> int:
    import app.jobs.tasks  # noqa: F401 - registers the jobs

    definition = JOBS.get(args.name)
    if definition is None:
        sys.stderr.write(f"Unknown job '{args.name}'. Known jobs: {', '.join(JOBS)}\n")
        return 2
    settings = get_settings()
    database = Database.from_settings(settings)
    try:
        ctx = JobContext(session_factory=database.session_factory, clock=Clock(), settings=settings)
        outcome = await run_job(definition, ctx, database.engine)
    finally:
        await database.dispose()
    return 0 if outcome is not JobOutcome.FAILED else 1


COMMANDS: dict[str, Callable[[argparse.Namespace], Coroutine[Any, Any, int]]] = {
    "wait-db": _wait_db,
    "seed": _seed,
    "list-jobs": _list_jobs,
    "run-job": _run_job,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    wait = commands.add_parser("wait-db", help="Wait until the database is reachable.")
    wait.add_argument("--timeout", type=int, default=60, help="Seconds (default 60).")
    seed = commands.add_parser("seed", help="Upsert reference data (system catalogs).")
    seed.add_argument("--demo", action="store_true", help="Also create demo data (dev only).")
    commands.add_parser("list-jobs", help="List registered background jobs.")
    run = commands.add_parser("run-job", help="Run a background job once.")
    run.add_argument("name")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    configure_logging(get_settings())
    return asyncio.run(COMMANDS[args.command](args))


if __name__ == "__main__":
    sys.exit(main())
