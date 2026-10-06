"""Part types and part replacements with lifetime status (clock: 2026-10-06)."""

from typing import Any

import pytest
from httpx import AsyncClient

from app.db.seeds import PART_TYPES
from tests.helpers import (
    API,
    AuthenticatedUser,
    create_garage,
    create_maintenance,
    create_part,
    create_vehicle,
    data,
    error,
    part_type_id,
    register_user,
)


@pytest.fixture
async def vehicle(client: AsyncClient, user: AuthenticatedUser) -> dict[str, Any]:
    return await create_vehicle(client, user, initial_mileage=60_000, current_mileage=99_200)


def url(vehicle: dict[str, Any]) -> str:
    return f"{API}/vehicles/{vehicle['id']}/parts"


async def test_part_type_catalog(client: AsyncClient, user: AuthenticatedUser) -> None:
    types = data(await client.get(f"{API}/part-types", headers=user.headers))
    assert {t["code"] for t in types} == {seed.code for seed in PART_TYPES}
    french = await register_user(client, preferred_language="fr")
    names = {t["name"] for t in data(await client.get(f"{API}/part-types", headers=french.headers))}
    assert "Plaquettes de frein" in names
    custom = data(
        await client.post(
            f"{API}/part-types", headers=user.headers, json={"name": "Turbo", "category": "engine"}
        ),
        201,
    )
    assert custom["is_system"] is False


async def test_create_with_type_defaults_and_lifetime(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    garage = await create_garage(client, user)
    part = await create_part(
        client,
        user,
        vehicle["id"],
        installed_mileage=60_000,
        brand="Bosch",
        reference_number="0 986 494 123",
        position="front",
        price="420.00",
        labor_cost="150.00",
        garage_id=garage["id"],
        warranty_expiration_date="2028-01-10",
    )
    assert part["part_name"] == "Brake pads"
    assert part["expected_lifetime_km"] == 40_000
    assert part["total_cost"] == "570.00"
    assert part["is_installed"] is True
    assert part["lifetime"] == {
        "next_replacement_date": None,
        "next_replacement_mileage": 100_000,
        "remaining_km": 800,
        "remaining_days": None,
        "status": "due_soon",
    }


async def test_new_part_supersedes_installed_one_at_same_position(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    old_front = await create_part(
        client, user, vehicle["id"], position="front", installed_mileage=60_000
    )
    rear = await create_part(client, user, vehicle["id"], position="rear", installed_mileage=60_000)
    new_front = await create_part(
        client,
        user,
        vehicle["id"],
        position="front",
        installed_date="2026-10-01",
        installed_mileage=99_000,
    )

    old = data(await client.get(f"{url(vehicle)}/{old_front['id']}", headers=user.headers))
    assert (old["removed_date"], old["removed_mileage"], old["is_installed"]) == (
        "2026-10-01",
        99_000,
        False,
    )
    assert old["lifetime"] is None

    installed = (
        await client.get(url(vehicle), headers=user.headers, params={"installed": "true"})
    ).json()
    assert {p["id"] for p in installed["data"]} == {rear["id"], new_front["id"]}


async def test_explicit_null_lifetime_and_maintenance_link(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    record = await create_maintenance(client, user, vehicle["id"], code="repair")
    part = await create_part(
        client,
        user,
        vehicle["id"],
        code="alternator",
        expected_lifetime_km=None,
        maintenance_record_id=record["id"],
    )
    assert part["lifetime"] is None
    assert part["maintenance_record_id"] == record["id"]

    other_vehicle = await create_vehicle(client, user)
    response = await client.post(
        f"{API}/vehicles/{other_vehicle['id']}/parts",
        headers=user.headers,
        json={
            "part_type_id": await part_type_id(client, user, "alternator"),
            "installed_date": "2026-01-10",
            "maintenance_record_id": record["id"],
        },
    )
    assert "maintenance_record_id" in error(response, 422, "VALIDATION_ERROR")["fields"]


async def test_time_based_lifetime(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    battery = await create_part(
        client, user, vehicle["id"], code="battery", installed_date="2022-09-01"
    )
    assert battery["lifetime"]["next_replacement_date"] == "2026-09-01"
    assert battery["lifetime"]["status"] == "overdue"


async def test_update_validation_and_delete(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    part = await create_part(client, user, vehicle["id"])
    item = f"{url(vehicle)}/{part['id']}"
    response = await client.patch(item, headers=user.headers, json={"removed_date": "2025-01-01"})
    assert "removed_date" in error(response, 422, "VALIDATION_ERROR")["fields"]
    removed = data(
        await client.patch(item, headers=user.headers, json={"removed_date": "2026-05-01"})
    )
    assert removed["is_installed"] is False

    bad_warranty = await client.post(
        url(vehicle),
        headers=user.headers,
        json={
            "part_type_id": part["part_type"]["id"],
            "installed_date": "2026-01-10",
            "warranty_expiration_date": "2025-01-01",
        },
    )
    error(bad_warranty, 422, "VALIDATION_ERROR")

    assert (await client.delete(item, headers=user.headers)).status_code == 204
    error(await client.get(item, headers=user.headers), 404, "NOT_FOUND")


async def test_search_and_odometer(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    await create_part(
        client,
        user,
        vehicle["id"],
        brand="Bosch",
        installed_date="2026-10-06",
        installed_mileage=99_500,
    )
    await create_part(client, user, vehicle["id"], code="battery", brand="Varta")
    found = (await client.get(url(vehicle), headers=user.headers, params={"q": "varta"})).json()[
        "data"
    ]
    assert [p["brand"] for p in found] == ["Varta"]
    current = data(await client.get(f"{API}/vehicles/{vehicle['id']}", headers=user.headers))
    assert current["current_mileage"] == 99_500
