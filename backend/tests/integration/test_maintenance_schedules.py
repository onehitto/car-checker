"""Maintenance schedules: deadlines, statuses and synchronisation with records.

The test clock is frozen at 2026-10-06.
"""

from typing import Any

import pytest
from httpx import AsyncClient

from tests.helpers import (
    API,
    AuthenticatedUser,
    create_maintenance,
    create_vehicle,
    data,
    error,
    maintenance_type_id,
)


@pytest.fixture
async def vehicle(client: AsyncClient, user: AuthenticatedUser) -> dict[str, Any]:
    return await create_vehicle(
        client, user, initial_mileage=40_000, current_mileage=59_400, purchase_date="2024-03-01"
    )


def url(vehicle: dict[str, Any]) -> str:
    return f"{API}/vehicles/{vehicle['id']}/maintenance-schedules"


async def create_schedule(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any], code: str, **fields: Any
) -> Any:
    payload = {"maintenance_type_id": await maintenance_type_id(client, user, code), **fields}
    return await client.post(url(vehicle), headers=user.headers, json=payload)


async def test_documented_example_from_latest_record(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    await create_maintenance(client, user, vehicle["id"], service_date="2025-11-01", mileage=50_000)
    schedule = data(await create_schedule(client, user, vehicle, "oil_change"), 201)

    assert (schedule["interval_km"], schedule["interval_months"]) == (10_000, 12)
    assert (schedule["last_service_date"], schedule["last_service_mileage"]) == (
        "2025-11-01",
        50_000,
    )
    assert (schedule["next_service_date"], schedule["next_service_mileage"]) == (
        "2026-11-01",
        60_000,
    )
    assert (schedule["remaining_km"], schedule["remaining_days"]) == (600, 26)
    assert schedule["status"] == "due_soon"
    assert schedule["due_reason"] == "both"
    assert schedule["maintenance_type"]["code"] == "oil_change"


async def test_new_record_moves_schedule_forward(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    await create_maintenance(client, user, vehicle["id"], service_date="2025-11-01", mileage=50_000)
    schedule = data(await create_schedule(client, user, vehicle, "oil_change"), 201)

    await create_maintenance(client, user, vehicle["id"], service_date="2026-10-06", mileage=59_400)
    refreshed = data(await client.get(f"{url(vehicle)}/{schedule['id']}", headers=user.headers))
    assert (refreshed["next_service_date"], refreshed["next_service_mileage"]) == (
        "2027-10-06",
        69_400,
    )
    assert refreshed["status"] == "ok"
    assert refreshed["due_reason"] is None


async def test_editing_or_deleting_the_last_record_recomputes(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    await create_maintenance(client, user, vehicle["id"], service_date="2025-11-01", mileage=50_000)
    typo = await create_maintenance(
        client, user, vehicle["id"], service_date="2026-10-01", mileage=590_000
    )
    schedule = data(await create_schedule(client, user, vehicle, "oil_change"), 201)
    assert schedule["last_service_mileage"] == 590_000

    records = f"{API}/vehicles/{vehicle['id']}/maintenance/{typo['id']}"
    await client.patch(records, headers=user.headers, json={"mileage": 59_000})
    fixed = data(await client.get(f"{url(vehicle)}/{schedule['id']}", headers=user.headers))
    assert fixed["last_service_mileage"] == 59_000
    assert fixed["next_service_mileage"] == 69_000

    await client.delete(records, headers=user.headers)
    reverted = data(await client.get(f"{url(vehicle)}/{schedule['id']}", headers=user.headers))
    assert (reverted["last_service_date"], reverted["last_service_mileage"]) == (
        "2025-11-01",
        50_000,
    )


async def test_vehicle_baseline_without_history(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    schedule = data(await create_schedule(client, user, vehicle, "timing_belt"), 201)
    # Bought 2024-03-01 at 40 000 km; every 100 000 km / 60 months.
    assert (schedule["next_service_date"], schedule["next_service_mileage"]) == (
        "2029-03-01",
        140_000,
    )
    assert schedule["status"] == "ok"


async def test_overdue_and_explicit_next(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    overdue = data(
        await create_schedule(
            client,
            user,
            vehicle,
            "air_filter",
            interval_km=15_000,
            interval_months=None,
            last_service_mileage=40_000,
            last_service_date="2024-03-01",
        ),
        201,
    )
    assert overdue["status"] == "overdue"
    assert overdue["overdue_km"] == 4_400
    assert overdue["overdue_days"] > 0

    explicit = data(
        await create_schedule(client, user, vehicle, "brake_pads", next_service_mileage=60_000),
        201,
    )
    assert (explicit["next_service_mileage"], explicit["remaining_km"]) == (60_000, 600)
    assert explicit["status"] == "due_soon"


async def test_status_filter_and_ordering(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    await create_schedule(client, user, vehicle, "timing_belt")
    await create_schedule(client, user, vehicle, "brake_pads", next_service_mileage=60_000)
    await create_schedule(client, user, vehicle, "spark_plugs", last_service_mileage=10_000)

    all_codes = [
        s["maintenance_type"]["code"]
        for s in data(await client.get(url(vehicle), headers=user.headers))
    ]
    assert all_codes == ["spark_plugs", "brake_pads", "timing_belt"]  # overdue, due_soon, ok

    filtered = data(
        await client.get(
            url(vehicle), headers=user.headers, params={"status": ["overdue", "due_soon"]}
        )
    )
    assert {s["status"] for s in filtered} == {"overdue", "due_soon"}


async def test_update_disable_and_delete(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    schedule = data(
        await create_schedule(client, user, vehicle, "spark_plugs", last_service_mileage=10_000),
        201,
    )
    item = f"{url(vehicle)}/{schedule['id']}"
    changed = data(await client.patch(item, headers=user.headers, json={"interval_km": 60_000}))
    assert changed["next_service_mileage"] == 70_000
    assert changed["status"] == "ok"

    disabled = data(
        await client.patch(
            item, headers=user.headers, json={"enabled": False, "interval_km": 20_000}
        )
    )
    assert disabled["status"] == "ok"
    assert disabled["remaining_km"] < 0

    assert (await client.delete(item, headers=user.headers)).status_code == 204
    error(await client.get(item, headers=user.headers), 404, "NOT_FOUND")


async def test_validation_and_conflicts(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    no_interval = await create_schedule(client, user, vehicle, "suspension")
    assert "interval_km" in error(no_interval, 422, "VALIDATION_ERROR")["fields"]

    await create_schedule(client, user, vehicle, "oil_change")
    error(await create_schedule(client, user, vehicle, "oil_change"), 409, "SCHEDULE_EXISTS")

    future = await create_schedule(client, user, vehicle, "coolant", last_service_date="2027-01-01")
    assert "last_service_date" in error(future, 422, "VALIDATION_ERROR")["fields"]

    negative = await create_schedule(client, user, vehicle, "coolant", warning_before_km=-1)
    assert "warning_before_km" in error(negative, 422, "VALIDATION_ERROR")["fields"]
