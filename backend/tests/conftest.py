"""Shared test fixtures.

Integration tests run against a real PostgreSQL database (`TEST_DATABASE_URL`). The schema is
built once per session with the Alembic migrations. Every test runs inside an outer
transaction that is rolled back; service-level commits become savepoints.
"""

from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import Connection, text
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.api.deps import get_db
from app.core.clock import FixedClock, get_clock
from app.core.config import Environment, Settings
from app.main import create_app
from tests.helpers import AuthenticatedUser, register_user

BACKEND_DIR = Path(__file__).resolve().parent.parent
NOW = datetime(2026, 10, 6, 10, 0, tzinfo=UTC)


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if "tests/integration" in str(item.path):
            item.add_marker(pytest.mark.integration)


@pytest.fixture(scope="session")
def settings(tmp_path_factory: pytest.TempPathFactory) -> Settings:
    base = Settings(_env_file=None)  # type: ignore[call-arg]
    return base.model_copy(
        update={
            "app_env": Environment.TEST,
            "database_url": base.test_database_url,
            "rate_limit_enabled": False,
            "email_backend": "memory",
            "upload_directory": tmp_path_factory.mktemp("uploads"),
            "log_level": "WARNING",
            "redis_url": None,
            # Cheap Argon2 parameters keep the suite fast; production values are enforced.
            "password_hash_time_cost": 1,
            "password_hash_memory_cost": 1024,
            "password_hash_parallelism": 1,
        }
    )


def _run_migrations(connection: Connection, database_url: str) -> None:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    config.attributes["connection"] = connection
    config.attributes["database_url"] = database_url
    config.attributes["skip_logging_config"] = True
    command.upgrade(config, "head")


@pytest.fixture(scope="session")
async def engine(settings: Settings) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    async with engine.begin() as connection:
        await connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        await connection.execute(text("CREATE SCHEMA public"))
        await connection.run_sync(_run_migrations, settings.database_url)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_connection(engine: AsyncEngine) -> AsyncIterator[AsyncConnection]:
    async with engine.connect() as connection:
        transaction = await connection.begin()
        yield connection
        await transaction.rollback()


@pytest.fixture
def session_factory(db_connection: AsyncConnection) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=db_connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
    )


@pytest.fixture
async def db_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock(NOW)


@pytest.fixture
def app_factory(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    clock: FixedClock,
) -> Callable[..., FastAPI]:
    """Build an app bound to the test transaction; keyword arguments override settings."""

    def build(**setting_overrides: Any) -> FastAPI:
        application = create_app(settings.model_copy(update=setting_overrides))

        async def override_get_db() -> AsyncIterator[AsyncSession]:
            async with session_factory() as session:
                yield session

        application.dependency_overrides[get_db] = override_get_db
        application.dependency_overrides[get_clock] = lambda: clock
        return application

    return build


@pytest.fixture
def app(app_factory: Callable[..., FastAPI]) -> FastAPI:
    return app_factory()


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client


@pytest.fixture
async def user(client: AsyncClient) -> AuthenticatedUser:
    return await register_user(client)


@pytest.fixture
async def other_user(client: AsyncClient) -> AuthenticatedUser:
    return await register_user(client)
