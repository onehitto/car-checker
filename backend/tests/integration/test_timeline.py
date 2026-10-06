"""Vehicle timeline."""

from typing import Any

import pytest
from httpx import AsyncClient

from tests.helpers import (
    API,
    AuthenticatedUser,
    create_document,
    create_expense,
    create_maintenance,
    create_part,
    create_vehicle,
    error,
)


@pytest.fixture
async def vehicle(client: AsyncClient, user: AuthenticatedUser) -> dict[str, Any]:
    vehicle = await create_vehicle(
        client, user, initial_mileage=50_000, current_mileage=50_000, purchase_date="2025-01-10"
    )
    await create_maintenance(
        client, user, vehicle["id"], service_date="2025-06-01", mileage=55_000, cost="400"
    )
    await create_maintenance(
        client,
        user,
        vehicle["id"],
        code="repair",
        kind="repair",
        title="Starter",
        service_date="2026-02-01",
        cost="900",
    )
    await create_part(client, user, vehicle["id"], installed_date="2026-03-01", price="300")
    await create_expense(
        client, user, vehicle["id"], title="Highway", category="tolls", expense_date="2026-04-01"
    )
    await create_document(
        client,
        user,
        vehicle["id"],
        title="AXA 2026",
        issue_date="2026-05-01",
        expiration_date="2027-05-01",
    )
    return vehicle


async def timeline(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any], **params: Any
) -> dict[str, Any]:
    response = await client.get(
        f"{API}/vehicles/{vehicle['id']}/timeline", headers=user.headers, params=params
    )
    assert response.status_code == 200, response.text
    return dict(response.json())


async def test_full_history_in_order(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    body = await timeline(client, user, vehicle)
    assert [(e["type"], e["date"]) for e in body["data"]] == [
        ("document", "2026-05-01"),
        ("expense", "2026-04-01"),
        ("part", "2026-03-01"),
        ("repair", "2026-02-01"),
        ("maintenance", "2025-06-01"),
        ("mileage", "2025-01-10"),
    ]
    part = body["data"][2]
    assert (part["title"], part["amount"], part["currency"]) == ("Brake pads", "300.00", "EUR")
    maintenance = body["data"][4]
    assert (maintenance["subtype"], maintenance["mileage"]) == ("oil_change", 55_000)
    # The expenses linked to the maintenance, the repair and the part are not repeated.
    assert body["meta"]["total"] == 6


async def test_filters_and_pagination(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    only = await timeline(client, user, vehicle, type=["maintenance", "repair"])
    assert [e["title"] for e in only["data"]] == ["Starter", "Oil change"]

    dated = await timeline(client, user, vehicle, date_from="2026-01-01", date_to="2026-03-31")
    assert [e["type"] for e in dated["data"]] == ["part", "repair"]

    page = await timeline(client, user, vehicle, limit=2, page=3)
    assert [e["type"] for e in page["data"]] == ["maintenance", "mileage"]
    assert page["meta"] == {"page": 3, "limit": 2, "total": 6, "total_pages": 3}


async def test_requires_access(
    client: AsyncClient, other_user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    error(
        await client.get(f"{API}/vehicles/{vehicle['id']}/timeline", headers=other_user.headers),
        404,
        "NOT_FOUND",
    )
    bad = await client.get(
        f"{API}/vehicles/{vehicle['id']}/timeline", headers=other_user.headers, params={"type": "x"}
    )
    assert bad.status_code in (404, 422)
