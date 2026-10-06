"""Fuel fill-ups, consumption, statistics and integrations."""

from typing import Any

import pytest
from httpx import AsyncClient

from tests.helpers import (
    API,
    AuthenticatedUser,
    create_fuel,
    create_vehicle,
    data,
    error,
    register_user,
)


@pytest.fixture
async def vehicle(client: AsyncClient, user: AuthenticatedUser) -> dict[str, Any]:
    return await create_vehicle(
        client, user, initial_mileage=80_000, current_mileage=80_000, purchase_date="2026-08-01"
    )


def url(vehicle: dict[str, Any]) -> str:
    return f"{API}/vehicles/{vehicle['id']}/fuel"


async def fill_series(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> list[dict[str, Any]]:
    return [
        await create_fuel(
            client,
            user,
            vehicle["id"],
            fill_date="2026-08-05",
            mileage=80_100,
            liters="45",
            price_per_liter="2.00",
        ),
        await create_fuel(
            client,
            user,
            vehicle["id"],
            fill_date="2026-08-20",
            mileage=80_400,
            liters="10",
            total_price="20.00",
            full_tank=False,
        ),
        await create_fuel(
            client,
            user,
            vehicle["id"],
            fill_date="2026-09-02",
            mileage=80_700,
            liters="32",
            price_per_liter="2.10",
            gas_station="Afriquia",
        ),
    ]


async def test_create_derives_prices_and_links_expense(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    record = await create_fuel(
        client, user, vehicle["id"], liters="42.3", price_per_liter="1.89", gas_station="Shell"
    )
    assert (record["total_price"], record["price_per_liter"]) == ("79.95", "1.8900")

    expenses = data(
        await client.get(f"{API}/vehicles/{vehicle['id']}/expenses", headers=user.headers)
    )
    assert [
        (e["source"], e["category"], e["amount"], e["title"], e["vendor"]) for e in expenses
    ] == [("fuel", "fuel", "79.95", "Fuel (42.3 L)", "Shell")]
    vehicle_now = data(await client.get(f"{API}/vehicles/{vehicle['id']}", headers=user.headers))
    assert vehicle_now["current_mileage"] == 80_500


async def test_consumption_per_fill_up(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    await fill_series(client, user, vehicle)
    records = data(await client.get(url(vehicle), headers=user.headers))
    by_mileage = {r["mileage"]: r for r in records}
    assert by_mileage[80_100]["consumption_l_100km"] is None
    assert by_mileage[80_400]["distance_since_previous"] == 300
    assert by_mileage[80_400]["consumption_l_100km"] is None
    # (10 + 32) L over 600 km.
    assert by_mileage[80_700]["consumption_l_100km"] == 7.0
    assert [r["mileage"] for r in records] == [80_700, 80_400, 80_100]


async def test_statistics_with_units(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    await fill_series(client, user, vehicle)
    stats = data(await client.get(f"{url(vehicle)}/statistics", headers=user.headers))
    assert stats["consumption_unit"] == "l_100km"
    assert (stats["fill_up_count"], stats["total_liters"], stats["total_cost"]) == (
        3,
        "87.000",
        "177.20",
    )
    assert stats["average_consumption"] == 7.0
    assert stats["cost_per_distance_unit"] == pytest.approx((20 + 67.2) / 600, abs=1e-4)
    assert [m["month"] for m in stats["monthly"]] == ["2026-08", "2026-09"]

    imperial = data(
        await client.get(
            f"{url(vehicle)}/statistics",
            headers=user.headers,
            params={"consumption_unit": "mpg_us", "distance_unit": "mi"},
        )
    )
    assert imperial["average_consumption"] == pytest.approx(33.6, abs=0.1)
    assert imperial["distance_tracked"] == pytest.approx(372.8, abs=0.1)

    french = await register_user(client, preferred_consumption_unit="km_l")
    other_vehicle = await create_vehicle(client, french)
    assert (
        data(
            await client.get(
                f"{API}/vehicles/{other_vehicle['id']}/fuel/statistics", headers=french.headers
            )
        )["consumption_unit"]
        == "km_l"
    )


async def test_validation(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    await create_fuel(client, user, vehicle["id"], fill_date="2026-09-01", mileage=80_500)
    cases = [
        ({"liters": "0"}, "liters"),
        ({"liters": "40", "price_per_liter": "2", "total_price": "100"}, "total_price"),
        ({"fill_date": "2026-10-20"}, "fill_date"),
        ({"fill_date": "2026-09-10", "mileage": 80_200}, "mileage"),
        ({"fuel_type": "kerosene"}, "fuel_type"),
    ]
    for payload, field in cases:
        body = {"fill_date": "2026-09-05", "mileage": 80_600, "liters": "30", **payload}
        response = await client.post(url(vehicle), headers=user.headers, json=body)
        assert field in error(response, 422, "VALIDATION_ERROR")["fields"], payload


async def test_update_and_delete_keep_expense_in_sync(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    record = await create_fuel(client, user, vehicle["id"], price_per_liter="2")
    item = f"{url(vehicle)}/{record['id']}"
    updated = data(await client.patch(item, headers=user.headers, json={"liters": "50"}))
    assert updated["total_price"] == "100.00"
    [expense] = data(
        await client.get(f"{API}/vehicles/{vehicle['id']}/expenses", headers=user.headers)
    )
    assert expense["amount"] == "100.00"

    assert (await client.delete(item, headers=user.headers)).status_code == 204
    assert (
        data(await client.get(f"{API}/vehicles/{vehicle['id']}/expenses", headers=user.headers))
        == []
    )
    error(await client.get(item, headers=user.headers), 404, "NOT_FOUND")


async def test_timeline_shows_fill_ups_once(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    await create_fuel(client, user, vehicle["id"], price_per_liter="2")
    events = data(
        await client.get(f"{API}/vehicles/{vehicle['id']}/timeline", headers=user.headers)
    )
    assert [(e["type"], e["title"], e["amount"]) for e in events if e["type"] != "mileage"] == [
        ("fuel", "40.00 L", "80.00")
    ]
