"""Vehicle and user dashboards (clock: 2026-10-06)."""

from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers import (
    API,
    AuthenticatedUser,
    create_document,
    create_expense,
    create_fuel,
    create_maintenance,
    create_part,
    create_vehicle,
    data,
    error,
    maintenance_type_id,
    share_vehicle_in_db,
)


async def add_schedule(
    client: AsyncClient, user: AuthenticatedUser, vehicle_id: str, code: str, **fields: Any
) -> None:
    payload = {"maintenance_type_id": await maintenance_type_id(client, user, code), **fields}
    response = await client.post(
        f"{API}/vehicles/{vehicle_id}/maintenance-schedules", headers=user.headers, json=payload
    )
    assert response.status_code == 201, response.text


@pytest.fixture
async def vehicle(client: AsyncClient, user: AuthenticatedUser) -> dict[str, Any]:
    vehicle = await create_vehicle(client, user, initial_mileage=40_000, current_mileage=59_400)
    vid = vehicle["id"]
    await add_schedule(
        client, user, vid, "oil_change", last_service_date="2025-11-01", last_service_mileage=50_000
    )
    await add_schedule(
        client,
        user,
        vid,
        "air_filter",
        interval_km=15_000,
        interval_months=None,
        last_service_mileage=40_000,
    )
    await add_schedule(client, user, vid, "timing_belt")
    await create_document(client, user, vid, title="AXA", expiration_date="2026-10-20")
    await create_document(
        client, user, vid, document_type="road_tax", title="Vignette", expiration_date="2026-01-31"
    )
    await create_part(client, user, vid, installed_mileage=20_000)
    await create_maintenance(
        client,
        user,
        vid,
        code="repair",
        kind="repair",
        title="Starter",
        service_date="2026-10-01",
        cost="900",
    )
    await create_expense(client, user, vid, amount="20", expense_date="2026-09-15")
    await create_fuel(
        client, user, vid, fill_date="2026-09-01", mileage=59_000, liters="40", total_price="80"
    )
    await create_fuel(
        client, user, vid, fill_date="2026-09-20", mileage=59_400, liters="26", total_price="52"
    )
    return vehicle


async def test_vehicle_dashboard(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    body = data(await client.get(f"{API}/vehicles/{vehicle['id']}/dashboard", headers=user.headers))
    assert body["current_mileage"] == 59_400
    assert body["vehicle"]["access_role"] == "owner"

    assert [s["maintenance_type"]["code"] for s in body["maintenance"]["overdue"]] == ["air_filter"]
    assert [s["maintenance_type"]["code"] for s in body["maintenance"]["upcoming"]] == [
        "oil_change"
    ]
    assert [d["title"] for d in body["documents"]["expired"]] == ["Vignette"]
    assert [d["title"] for d in body["documents"]["expiring"]] == ["AXA"]
    assert [p["part_name"] for p in body["worn_parts"]] == ["Brake pads"]

    # 100 - 25 (overdue) - 5 (due soon) - 25 (expired) - 5 (expiring) - 5 (worn part)
    assert body["health"] == {
        "score": 35,
        "level": "critical",
        "overdue_maintenance": 1,
        "due_maintenance": 1,
        "expired_documents": 1,
        "expiring_documents": 1,
        "worn_parts": 1,
    }
    assert body["alerts"]["summary"]["open"] == 5
    assert len(body["alerts"]["latest"]) == 5
    assert [r["title"] for r in body["recent_maintenance"]] == ["Starter"]
    assert len(body["recent_expenses"]) == 4

    assert body["fuel"]["average_consumption_l_100km"] == 6.5
    costs = body["costs"]
    assert (costs["currency"], costs["total"], costs["this_month"], costs["this_year"]) == (
        "EUR",
        "1052.00",
        "900.00",
        "1052.00",
    )
    assert costs["total_maintenance_cost"] == "900.00"
    assert costs["monthly"][0]["month"] == "2025-11"
    assert costs["monthly"][-1] == {"month": "2026-10", "total": "900.00"}


async def test_global_dashboard(
    client: AsyncClient,
    db_session: AsyncSession,
    user: AuthenticatedUser,
    other_user: AuthenticatedUser,
    vehicle: dict[str, Any],
) -> None:
    clean = await create_vehicle(client, user, brand="Renault", model="Clio", currency="MAD")
    await create_vehicle(client, user, brand="Old", status="sold")
    shared = await create_vehicle(client, other_user, brand="Peugeot", model="208")
    await share_vehicle_in_db(db_session, shared["id"], user.id, "viewer")

    body = data(await client.get(f"{API}/dashboard", headers=user.headers))
    assert body["totals"] == {
        "vehicles": 3,
        "overdue_maintenance": 1,
        "due_maintenance": 1,
        "expired_documents": 1,
        "expiring_documents": 1,
        "open_alerts": 5,
    }
    # Least healthy first.
    assert body["vehicles"][0]["vehicle"]["id"] == vehicle["id"]
    assert {v["vehicle"]["id"]: v["vehicle"]["access_role"] for v in body["vehicles"]}[
        shared["id"]
    ] == "viewer"
    first = body["vehicles"][0]
    assert (first["open_alerts"], first["next_maintenance"]["maintenance_type"]["code"]) == (
        5,
        "air_filter",
    )
    clean_overview = next(v for v in body["vehicles"] if v["vehicle"]["id"] == clean["id"])
    assert (clean_overview["health"]["score"], clean_overview["next_maintenance"]) == (100, None)

    assert [
        (u["maintenance_type"]["code"], u["vehicle_name"]) for u in body["upcoming_maintenance"]
    ] == [
        ("air_filter", "Dacia Logan"),
        ("oil_change", "Dacia Logan"),
    ]
    assert [d["title"] for d in body["expiring_documents"]] == ["Vignette", "AXA"]
    assert body["costs"] == [{"currency": "EUR", "this_month": "900.00", "this_year": "1052.00"}]


async def test_dashboard_for_new_user_is_empty(
    client: AsyncClient, other_user: AuthenticatedUser
) -> None:
    body = data(await client.get(f"{API}/dashboard", headers=other_user.headers))
    assert body["totals"]["vehicles"] == 0
    assert body["vehicles"] == [] and body["costs"] == []


async def test_vehicle_dashboard_requires_access(
    client: AsyncClient, other_user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    error(
        await client.get(f"{API}/vehicles/{vehicle['id']}/dashboard", headers=other_user.headers),
        404,
        "NOT_FOUND",
    )
