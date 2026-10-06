"""Statistics (clock: 2026-10-06)."""

from typing import Any

import pytest
from httpx import AsyncClient

from tests.helpers import (
    API,
    AuthenticatedUser,
    create_expense,
    create_fuel,
    create_maintenance,
    create_vehicle,
    data,
    error,
)


@pytest.fixture
async def vehicle(client: AsyncClient, user: AuthenticatedUser) -> dict[str, Any]:
    vehicle = await create_vehicle(
        client, user, initial_mileage=80_000, current_mileage=80_000, purchase_date="2025-10-01"
    )
    vid = vehicle["id"]
    await create_maintenance(
        client, user, vid, service_date="2025-11-02", mileage=81_000, cost="400"
    )
    await create_maintenance(
        client, user, vid, service_date="2026-05-01", mileage=86_000, cost="450"
    )
    await create_maintenance(
        client,
        user,
        vid,
        code="repair",
        kind="repair",
        title="Alternator",
        service_date="2026-03-10",
        cost="2100",
    )
    await create_maintenance(
        client,
        user,
        vid,
        code="repair",
        kind="repair",
        title="Exhaust",
        service_date="2026-07-01",
        cost="300",
    )
    await create_expense(
        client,
        user,
        vid,
        category="insurance",
        title="AXA",
        amount="3000",
        expense_date="2026-01-05",
    )
    await create_fuel(
        client, user, vid, fill_date="2026-09-01", mileage=89_000, liters="40", total_price="80"
    )
    await create_fuel(
        client, user, vid, fill_date="2026-09-20", mileage=89_500, liters="30", total_price="60"
    )
    await client.post(
        f"{API}/vehicles/{vid}/mileage", headers=user.headers, json={"mileage": 90_000}
    )
    return vehicle


async def stats(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any], **params: Any
) -> dict[str, Any]:
    return dict(
        data(
            await client.get(
                f"{API}/vehicles/{vehicle['id']}/statistics", headers=user.headers, params=params
            )
        )
    )


async def test_vehicle_statistics_since_first_expense(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    body = await stats(client, user, vehicle)
    assert body["period"] == {"date_from": "2025-11-02", "date_to": "2026-10-06", "months": 12}
    assert body["total"] == "6390.00"
    assert [(c["category"], c["total"], c["count"]) for c in body["by_category"]] == [
        ("insurance", "3000.00", 1),
        ("repairs", "2400.00", 2),
        ("maintenance", "850.00", 2),
        ("fuel", "140.00", 2),
    ]
    assert body["average_monthly_cost"] == "532.50"
    assert body["distance_driven_km"] == 9_000
    assert body["cost_per_km"] == pytest.approx(0.71, abs=0.001)
    assert (body["maintenance_count"], body["repair_count"]) == (2, 2)
    assert [r["title"] for r in body["most_expensive_repairs"]] == ["Alternator", "Exhaust"]
    oil = next(
        f for f in body["maintenance_frequency"] if f["maintenance_type"]["code"] == "oil_change"
    )
    assert (oil["count"], oil["average_interval_days"], oil["average_interval_km"]) == (
        2,
        180,
        5_000,
    )
    assert body["fuel"]["average_consumption_l_100km"] == 6.0
    assert [y["year"] for y in body["by_year"]] == [2025, 2026]


async def test_year_and_category_filters(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    body = await stats(client, user, vehicle, year=2026, category=["repairs", "fuel"])
    assert body["period"]["date_from"] == "2026-01-01"
    assert body["total"] == "2540.00"
    assert body["by_month"] == [
        {"month": "2026-03", "total": "2100.00"},
        {"month": "2026-07", "total": "300.00"},
        {"month": "2026-09", "total": "140.00"},
    ]
    response = await client.get(
        f"{API}/vehicles/{vehicle['id']}/statistics",
        headers=user.headers,
        params={"year": 2026, "date_from": "2026-01-01"},
    )
    assert "year" in error(response, 422, "VALIDATION_ERROR")["fields"]


async def test_global_statistics_group_by_currency(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    moroccan = await create_vehicle(client, user, currency="MAD", nickname="Duster")
    await create_expense(client, user, moroccan["id"], amount="500", expense_date="2026-09-01")
    body = data(await client.get(f"{API}/statistics", headers=user.headers, params={"year": 2026}))
    assert [(c["currency"], c["total"]) for c in body["currencies"]] == [
        ("EUR", "5990.00"),
        ("MAD", "500.00"),
    ]
    mad = body["currencies"][1]
    assert mad["by_vehicle"] == [
        {"vehicle_id": moroccan["id"], "display_name": "Duster", "total": "500.00"}
    ]

    only_one = data(
        await client.get(
            f"{API}/statistics", headers=user.headers, params={"vehicle_id": moroccan["id"]}
        )
    )
    assert [c["currency"] for c in only_one["currencies"]] == ["MAD"]
