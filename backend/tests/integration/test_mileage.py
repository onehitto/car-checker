"""Mileage history and odometer validation."""

from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers import (
    API,
    AuthenticatedUser,
    create_vehicle,
    data,
    error,
    share_vehicle_in_db,
)


@pytest.fixture
async def vehicle(client: AsyncClient, user: AuthenticatedUser) -> dict[str, Any]:
    return await create_vehicle(
        client, user, initial_mileage=80_000, current_mileage=85_000, purchase_date="2025-01-15"
    )


def url(vehicle: dict[str, Any]) -> str:
    return f"{API}/vehicles/{vehicle['id']}/mileage"


async def add(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any], **body: Any
) -> Any:
    return await client.post(url(vehicle), headers=user.headers, json=body)


async def current_mileage(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> int:
    response = await client.get(f"{API}/vehicles/{vehicle['id']}", headers=user.headers)
    return int(data(response)["current_mileage"])


async def test_vehicle_creation_records_initial_history(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    body = (await client.get(url(vehicle), headers=user.headers)).json()
    assert [(e["mileage"], e["recorded_on"], e["source"]) for e in body["data"]] == [
        (85_000, "2026-10-06", "manual"),
        (80_000, "2025-01-15", "initial"),
    ]


async def test_new_reading_updates_current_mileage(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    result = data(await add(client, user, vehicle, mileage=86_500, notes="Road trip"), 201)
    assert result["current_mileage"] == 86_500
    assert result["entry"]["source"] == "manual"
    assert result["entry"]["recorded_on"] == "2026-10-06"
    assert await current_mileage(client, user, vehicle) == 86_500


async def test_lower_reading_is_refused(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    err = error(await add(client, user, vehicle, mileage=1_200), 422, "MILEAGE_DECREASE")
    assert err["fields"] == {"mileage": "Must be greater than or equal to 85000."}
    assert await current_mileage(client, user, vehicle) == 85_000


async def test_force_accepts_lower_reading(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    result = data(await add(client, user, vehicle, mileage=1_200, force=True), 201)
    assert result["current_mileage"] == 1_200


async def test_backdated_reading_must_fit_between_neighbours(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    # Between 2025-01-15 (80 000) and today (85 000).
    ok = data(await add(client, user, vehicle, mileage=82_000, recorded_on="2025-06-01"), 201)
    assert ok["current_mileage"] == 85_000  # not the newest reading

    too_high = await add(client, user, vehicle, mileage=90_000, recorded_on="2025-07-01")
    assert "mileage" in error(too_high, 422, "VALIDATION_ERROR")["fields"]
    too_low = await add(client, user, vehicle, mileage=81_000, recorded_on="2025-07-01")
    error(too_low, 422, "MILEAGE_DECREASE")


async def test_future_and_negative_readings(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    future = await add(client, user, vehicle, mileage=90_000, recorded_on="2026-10-20")
    assert "recorded_on" in error(future, 422, "VALIDATION_ERROR")["fields"]
    negative = await add(client, user, vehicle, mileage=-1)
    assert "mileage" in error(negative, 422, "VALIDATION_ERROR")["fields"]


async def test_update_without_history(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    result = data(await add(client, user, vehicle, mileage=87_000, record_history=False), 201)
    assert result == {"current_mileage": 87_000, "entry": None}
    total = (await client.get(url(vehicle), headers=user.headers)).json()["meta"]["total"]
    assert total == 2


async def test_delete_reading_recomputes_current_mileage(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    entry = data(await add(client, user, vehicle, mileage=88_000), 201)["entry"]
    response = await client.delete(f"{url(vehicle)}/{entry['id']}", headers=user.headers)
    assert response.status_code == 204
    assert await current_mileage(client, user, vehicle) == 85_000
    error(
        await client.delete(f"{url(vehicle)}/{entry['id']}", headers=user.headers), 404, "NOT_FOUND"
    )


async def test_filters_and_permissions(
    client: AsyncClient,
    db_session: AsyncSession,
    user: AuthenticatedUser,
    other_user: AuthenticatedUser,
    vehicle: dict[str, Any],
) -> None:
    filtered = (
        await client.get(url(vehicle), headers=user.headers, params={"source": "initial"})
    ).json()
    assert filtered["meta"]["total"] == 1

    error(await client.get(url(vehicle), headers=other_user.headers), 404, "NOT_FOUND")
    await share_vehicle_in_db(db_session, vehicle["id"], other_user.id, "viewer")
    assert (await client.get(url(vehicle), headers=other_user.headers)).status_code == 200
    error(await add(client, other_user, vehicle, mileage=90_000), 403, "FORBIDDEN")
