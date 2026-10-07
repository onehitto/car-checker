"""Error mapping for unexpected failures and degraded dependencies."""

from collections.abc import AsyncIterator, Callable
from typing import Any

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import IntegrityError

from app.api.deps import get_db


async def request(app: FastAPI, path: str) -> Any:
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
    ) as client:
        return await client.get(path)


async def test_unexpected_exception_returns_generic_500(
    app_factory: Callable[..., FastAPI],
) -> None:
    app = app_factory()

    async def boom() -> None:
        raise RuntimeError("database password is hunter2")

    app.add_api_route("/boom", boom)
    response = await request(app, "/boom")
    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "INTERNAL_ERROR"
    assert "hunter2" not in response.text
    assert body["error"]["request_id"]


async def test_integrity_error_becomes_conflict(app_factory: Callable[..., FastAPI]) -> None:
    app = app_factory()

    async def race() -> None:
        raise IntegrityError("INSERT ...", {"secret": "x"}, Exception("duplicate key"))

    app.add_api_route("/race", race)
    response = await request(app, "/race")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"
    assert "INSERT" not in response.text


async def test_health_reports_unavailable_database(app_factory: Callable[..., FastAPI]) -> None:
    app = app_factory()

    class BrokenSession:
        async def execute(self, *_: Any) -> None:
            raise ConnectionRefusedError("db down")

    async def broken_db() -> AsyncIterator[BrokenSession]:
        yield BrokenSession()

    app.dependency_overrides[get_db] = broken_db
    response = await request(app, "/health")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "SERVICE_UNAVAILABLE"
    assert "db down" not in response.text


async def test_method_not_allowed_uses_envelope(client: AsyncClient) -> None:
    response = await client.put("/health")
    assert response.status_code == 405
    assert response.json()["error"]["code"] == "METHOD_NOT_ALLOWED"
