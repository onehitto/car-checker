"""Oil changes extend maintenance records."""

from typing import Any

import pytest
from httpx import AsyncClient

from tests.helpers import (
    API,
    AuthenticatedUser,
    create_garage,
    create_vehicle,
    data,
    error,
    maintenance_type_id,
)

OIL = {
    "service_date": "2026-10-06",
    "mileage": 90_150,
    "cost": "450.00",
    "oil_brand": "Total",
    "oil_type": "synthetic",
    "oil_viscosity": "5W-30",
    "oil_quantity_liters": "4.80",
    "oil_filter_changed": True,
    "filter_brand": "Purflux",
}


@pytest.fixture
async def vehicle(client: AsyncClient, user: AuthenticatedUser) -> dict[str, Any]:
    return await create_vehicle(client, user, initial_mileage=80_000, current_mileage=89_000)


def url(vehicle: dict[str, Any]) -> str:
    return f"{API}/vehicles/{vehicle['id']}/oil-changes"


async def add_schedule(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any], code: str
) -> str:
    response = await client.post(
        f"{API}/vehicles/{vehicle['id']}/maintenance-schedules",
        headers=user.headers,
        json={"maintenance_type_id": await maintenance_type_id(client, user, code)},
    )
    return str(data(response, 201)["id"])


async def test_documented_oil_change_effects(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    oil_schedule = await add_schedule(client, user, vehicle, "oil_change")
    filter_schedule = await add_schedule(client, user, vehicle, "oil_filter")
    garage = await create_garage(client, user)

    oil = data(
        await client.post(
            url(vehicle), headers=user.headers, json={**OIL, "garage_id": garage["id"]}
        ),
        201,
    )
    assert oil["maintenance_type"]["code"] == "oil_change"
    assert (oil["oil_viscosity"], oil["oil_quantity_liters"], oil["oil_filter_changed"]) == (
        "5W-30",
        "4.80",
        True,
    )
    assert oil["garage"]["id"] == garage["id"]

    schedules = f"{API}/vehicles/{vehicle['id']}/maintenance-schedules"
    oil_next = data(await client.get(f"{schedules}/{oil_schedule}", headers=user.headers))
    assert (oil_next["next_service_mileage"], oil_next["next_service_date"]) == (
        100_150,
        "2027-10-06",
    )
    filter_next = data(await client.get(f"{schedules}/{filter_schedule}", headers=user.headers))
    assert filter_next["last_service_mileage"] == 90_150

    [expense] = data(
        await client.get(f"{API}/vehicles/{vehicle['id']}/expenses", headers=user.headers)
    )
    assert (expense["amount"], expense["category"]) == ("450.00", "maintenance")
    assert (
        data(await client.get(f"{API}/vehicles/{vehicle['id']}", headers=user.headers))[
            "current_mileage"
        ]
        == 90_150
    )

    # It is a regular maintenance record too.
    records = data(
        await client.get(f"{API}/vehicles/{vehicle['id']}/maintenance", headers=user.headers)
    )
    assert [r["id"] for r in records] == [oil["id"]]


async def test_update_list_and_delete(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    oil = data(await client.post(url(vehicle), headers=user.headers, json=OIL), 201)
    item = f"{url(vehicle)}/{oil['id']}"
    updated = data(
        await client.patch(
            item, headers=user.headers, json={"oil_viscosity": "0W-20", "cost": "500"}
        )
    )
    assert (updated["oil_viscosity"], updated["cost"], updated["oil_brand"]) == (
        "0W-20",
        "500.00",
        "Total",
    )

    listed = (await client.get(url(vehicle), headers=user.headers)).json()
    assert [o["id"] for o in listed["data"]] == [oil["id"]]

    assert (await client.delete(item, headers=user.headers)).status_code == 204
    error(await client.get(item, headers=user.headers), 404, "NOT_FOUND")
    assert (
        data(await client.get(f"{API}/vehicles/{vehicle['id']}/expenses", headers=user.headers))
        == []
    )


async def test_validation_and_regular_records_are_not_oil_changes(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    response = await client.post(
        url(vehicle), headers=user.headers, json={**OIL, "oil_viscosity": "thick"}
    )
    assert "oil_viscosity" in error(response, 422, "VALIDATION_ERROR")["fields"]

    record = data(
        await client.post(
            f"{API}/vehicles/{vehicle['id']}/maintenance",
            headers=user.headers,
            json={
                "maintenance_type_id": await maintenance_type_id(client, user, "oil_change"),
                "service_date": "2026-09-01",
            },
        ),
        201,
    )
    error(
        await client.get(f"{url(vehicle)}/{record['id']}", headers=user.headers), 404, "NOT_FOUND"
    )
