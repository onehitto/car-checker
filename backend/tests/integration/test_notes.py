"""Notes about a vehicle or one of its records."""

from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.clock import FixedClock
from app.core.config import Settings
from app.jobs.registry import JobContext
from app.jobs.tasks import cleanup_orphan_files
from tests.helpers import API, AuthenticatedUser, create_maintenance, create_vehicle, data, error


@pytest.fixture
async def vehicle(client: AsyncClient, user: AuthenticatedUser) -> dict[str, Any]:
    return await create_vehicle(client, user)


def url(vehicle: dict[str, Any]) -> str:
    return f"{API}/vehicles/{vehicle['id']}/notes"


async def add_note(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any], **fields: Any
) -> dict[str, Any]:
    return dict(
        data(
            await client.post(url(vehicle), headers=user.headers, json={"body": "Note", **fields}),
            201,
        )
    )


async def test_crud_and_ordering(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    first = await add_note(
        client, user, vehicle, title="Noise", body="Rattling when braking", category="problem"
    )
    pinned = await add_note(client, user, vehicle, body="Spare key in the drawer", is_pinned=True)
    await add_note(client, user, vehicle, body="Washed")
    assert first["user_id"] == user.id

    listed = (await client.get(url(vehicle), headers=user.headers)).json()["data"]
    assert listed[0]["id"] == pinned["id"]
    problems = (
        await client.get(url(vehicle), headers=user.headers, params={"category": "problem"})
    ).json()["data"]
    assert [n["id"] for n in problems] == [first["id"]]
    found = (await client.get(url(vehicle), headers=user.headers, params={"q": "rattling"})).json()[
        "data"
    ]
    assert [n["id"] for n in found] == [first["id"]]

    item = f"{url(vehicle)}/{first['id']}"
    updated = data(
        await client.patch(item, headers=user.headers, json={"is_pinned": True, "title": None})
    )
    assert (updated["is_pinned"], updated["title"]) == (True, None)
    error(
        await client.patch(item, headers=user.headers, json={"body": None}), 422, "VALIDATION_ERROR"
    )
    assert (await client.delete(item, headers=user.headers)).status_code == 204
    error(await client.get(item, headers=user.headers), 404, "NOT_FOUND")


async def test_note_about_a_record(
    client: AsyncClient,
    user: AuthenticatedUser,
    vehicle: dict[str, Any],
    session_factory: async_sessionmaker[AsyncSession],
    clock: FixedClock,
    settings: Settings,
) -> None:
    record = await create_maintenance(client, user, vehicle["id"])
    note = await add_note(
        client,
        user,
        vehicle,
        entity_type="maintenance_record",
        entity_id=record["id"],
        category="maintenance",
    )
    by_record = (
        await client.get(url(vehicle), headers=user.headers, params={"entity_id": record["id"]})
    ).json()
    assert [n["id"] for n in by_record["data"]] == [note["id"]]

    other_vehicle = await create_vehicle(client, user)
    foreign = await client.post(
        f"{API}/vehicles/{other_vehicle['id']}/notes",
        headers=user.headers,
        json={"body": "x", "entity_type": "maintenance_record", "entity_id": record["id"]},
    )
    assert "entity_id" in error(foreign, 422, "VALIDATION_ERROR")["fields"]
    half = await client.post(
        url(vehicle), headers=user.headers, json={"body": "x", "entity_type": "expense"}
    )
    error(half, 422, "VALIDATION_ERROR")

    # Deleting the record keeps the note, detached by the cleanup job.
    await client.delete(
        f"{API}/vehicles/{vehicle['id']}/maintenance/{record['id']}", headers=user.headers
    )
    ctx = JobContext(session_factory=session_factory, clock=clock, settings=settings)
    assert (await cleanup_orphan_files(ctx))["detached_notes"] == 1
    kept = data(await client.get(f"{url(vehicle)}/{note['id']}", headers=user.headers))
    assert (kept["entity_type"], kept["entity_id"], kept["body"]) == (None, None, "Note")


async def test_viewer_reads_only(
    client: AsyncClient,
    db_session: AsyncSession,
    user: AuthenticatedUser,
    other_user: AuthenticatedUser,
    vehicle: dict[str, Any],
) -> None:
    from tests.helpers import share_vehicle_in_db

    await add_note(client, user, vehicle)
    await share_vehicle_in_db(db_session, vehicle["id"], other_user.id, "viewer")
    assert (await client.get(url(vehicle), headers=other_user.headers)).json()["meta"]["total"] == 1
    error(
        await client.post(url(vehicle), headers=other_user.headers, json={"body": "x"}),
        403,
        "FORBIDDEN",
    )
