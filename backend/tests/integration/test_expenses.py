"""Expenses: manual entries and expenses linked to maintenance records and parts."""

from typing import Any

import pytest
from httpx import AsyncClient

from tests.helpers import (
    API,
    AuthenticatedUser,
    create_expense,
    create_maintenance,
    create_part,
    create_vehicle,
    data,
    error,
    register_user,
)


@pytest.fixture
async def vehicle(client: AsyncClient, user: AuthenticatedUser) -> dict[str, Any]:
    return await create_vehicle(client, user)


def url(vehicle: dict[str, Any]) -> str:
    return f"{API}/vehicles/{vehicle['id']}/expenses"


async def list_expenses(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any], **params: Any
) -> list[dict[str, Any]]:
    return list(
        (await client.get(url(vehicle), headers=user.headers, params=params)).json()["data"]
    )


async def test_manual_expense_crud(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    expense = await create_expense(
        client, user, vehicle["id"], vendor="Parking Maarif", mileage=81_000
    )
    assert expense["source"] == "manual"
    assert expense["currency"] == "EUR"
    item = f"{url(vehicle)}/{expense['id']}"

    updated = data(await client.patch(item, headers=user.headers, json={"amount": "25.50"}))
    assert updated["amount"] == "25.50"
    assert (await client.delete(item, headers=user.headers)).status_code == 204
    error(await client.get(item, headers=user.headers), 404, "NOT_FOUND")


async def test_validation(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    for payload, field in (
        ({"amount": "-1"}, "amount"),
        ({"amount": "1.234"}, "amount"),
        ({"category": "food"}, "category"),
        ({"expense_date": "2027-01-01"}, "expense_date"),
        ({"mileage": -1}, "mileage"),
    ):
        body = {
            "category": "parking",
            "title": "P",
            "amount": "1",
            "expense_date": "2026-09-01",
            **payload,
        }
        response = await client.post(url(vehicle), headers=user.headers, json=body)
        assert field in error(response, 422, "VALIDATION_ERROR")["fields"], payload


async def test_maintenance_record_maintains_its_expense(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    record = await create_maintenance(client, user, vehicle["id"], cost="450.00")
    [expense] = await list_expenses(client, user, vehicle)
    assert (expense["source"], expense["source_id"], expense["category"]) == (
        "maintenance",
        record["id"],
        "maintenance",
    )
    assert (expense["amount"], expense["title"], expense["expense_date"]) == (
        "450.00",
        "Oil change",
        "2026-09-01",
    )

    record_url = f"{API}/vehicles/{vehicle['id']}/maintenance/{record['id']}"
    await client.patch(record_url, headers=user.headers, json={"cost": "500.00", "kind": "repair"})
    [expense] = await list_expenses(client, user, vehicle)
    assert (expense["amount"], expense["category"]) == ("500.00", "repairs")

    # Linked expenses are read-only through the expense endpoints.
    item = f"{url(vehicle)}/{expense['id']}"
    error(
        await client.patch(item, headers=user.headers, json={"amount": "1"}),
        409,
        "EXPENSE_LINKED_TO_SOURCE",
    )
    error(await client.delete(item, headers=user.headers), 409, "EXPENSE_LINKED_TO_SOURCE")

    await client.patch(record_url, headers=user.headers, json={"cost": None})
    assert await list_expenses(client, user, vehicle) == []

    await client.patch(record_url, headers=user.headers, json={"cost": "90"})
    await client.delete(record_url, headers=user.headers)
    assert await list_expenses(client, user, vehicle) == []


async def test_part_purchase_expense_unless_installed_during_maintenance(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    standalone = await create_part(
        client, user, vehicle["id"], price="300", labor_cost="50", brand="Bosch"
    )
    record = await create_maintenance(client, user, vehicle["id"], code="brake_pads", cost="600")
    await create_part(
        client,
        user,
        vehicle["id"],
        price="200",
        maintenance_record_id=record["id"],
        position="rear",
    )

    expenses = await list_expenses(client, user, vehicle, sort="amount")
    assert [(e["source"], e["amount"]) for e in expenses] == [
        ("part", "350.00"),
        ("maintenance", "600.00"),
    ]
    assert expenses[0]["source_id"] == standalone["id"]
    assert expenses[0]["category"] == "parts"


async def test_filters(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    await create_expense(
        client, user, vehicle["id"], category="tolls", title="Highway A1", amount="45"
    )
    await create_expense(
        client, user, vehicle["id"], category="washing", title="Car wash", amount="8"
    )
    await create_expense(
        client,
        user,
        vehicle["id"],
        category="fines",
        title="Speeding",
        amount="300",
        expense_date="2026-03-01",
    )
    await create_maintenance(client, user, vehicle["id"], cost="450")

    titles = lambda items: sorted(e["title"] for e in items)  # noqa: E731
    assert titles(await list_expenses(client, user, vehicle, category=["tolls", "washing"])) == [
        "Car wash",
        "Highway A1",
    ]
    assert titles(
        await list_expenses(client, user, vehicle, amount_min="100", amount_max="400")
    ) == ["Speeding"]
    assert titles(await list_expenses(client, user, vehicle, date_to="2026-06-30")) == ["Speeding"]
    assert titles(await list_expenses(client, user, vehicle, source="maintenance")) == [
        "Oil change"
    ]
    assert len(await list_expenses(client, user, vehicle, source="manual")) == 3
    assert titles(await list_expenses(client, user, vehicle, q="highway")) == ["Highway A1"]


async def test_global_listing_reports_each_vehicle_currency(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    moroccan = await create_vehicle(client, user, currency="MAD")
    await create_expense(client, user, vehicle["id"])
    await create_expense(client, user, moroccan["id"], amount="150")
    stranger = await register_user(client)
    await create_expense(client, stranger, (await create_vehicle(client, stranger))["id"])

    body = (
        await client.get(f"{API}/expenses", headers=user.headers, params={"sort": "amount"})
    ).json()
    assert [(e["amount"], e["currency"]) for e in body["data"]] == [
        ("20.00", "EUR"),
        ("150.00", "MAD"),
    ]
