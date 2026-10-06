"""Management commands.

python -m app.cli seed            # upsert reference data (system catalogs)
"""

import argparse
import asyncio
import sys
from collections.abc import Awaitable, Callable, Sequence

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.db.seeds import seed_reference_data
from app.db.session import Database

logger = get_logger("app.cli")


async def _seed(_args: argparse.Namespace) -> int:
    database = Database.from_settings(get_settings())
    try:
        async with database.session_factory() as session:
            counts = await seed_reference_data(session)
            await session.commit()
    finally:
        await database.dispose()
    logger.info("seed_completed", **counts)
    return 0


COMMANDS: dict[str, Callable[[argparse.Namespace], Awaitable[int]]] = {"seed": _seed}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("seed", help="Upsert reference data (system catalogs).")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    configure_logging(get_settings())
    return asyncio.run(COMMANDS[args.command](args))


if __name__ == "__main__":
    sys.exit(main())
