"""The Alembic migrations must produce exactly the schema described by the ORM models."""

from typing import Any

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import Connection
from sqlalchemy.ext.asyncio import AsyncConnection

from app.db.all_models import Base


def _diff(connection: Connection) -> list[Any]:
    context = MigrationContext.configure(connection, opts={"compare_type": True})
    return list(compare_metadata(context, Base.metadata))


async def test_models_and_migrations_are_in_sync(db_connection: AsyncConnection) -> None:
    assert await db_connection.run_sync(_diff) == []
