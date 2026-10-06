"""Maintenance records: CRUD, filters, odometer integration and authorization."""

from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers import (
    API,
    AuthenticatedUser,
    create_garage,
    create_maintenance,
    create_vehicle,
    data,
    error,
    maintenance_type_id,
    register_user,
    share_vehicle_in_db,
)


@pytest.fixture
async def vehicle(client: AsyncClient, user: AuthenticatedUser) -> dict[str, Any]:
    return await create_vehicle(client, user, initial_mileage=80_000, current_mileage=85_000)


def records_url(vehicle: dict[str, Any]) -> str:
    return f"{API}/vehicles/{vehicle['id']}/maintenance"


async def test_create_with_defaults(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    garage = await create_garage(client, user)
    record = await create_maintenance(
        client,
        user,
        vehicle["id"],
        service_date="2026-10-06",
        mileage=86_000,
        labor_cost="150.00",
        parts_cost="300.50",
        garage_id=garage["id"],
    )
    assert record["title"] == "Oil change"
    assert record["kind"] == "maintenance"
    assert record["cost"] == "450.50"
    assert record["maintenance_type"]["code"] == "oil_change"
    assert record["garage"]["name"] == "Garage Atlas"

    # The record advanced the odometer and wrote a history entry.
    vehicle_now = data(await client.get(f"{API}/vehicles/{vehicle['id']}", headers=user.headers))
    assert vehicle_now["current_mileage"] == 86_000
    history = data(
        await client.get(
            f"{API}/vehicles/{vehicle['id']}/mileage",
            headers=user.headers,
            params={"source": "maintenance"},
        )
    )
    assert [(h["mileage"], h["recorded_on"]) for h in history] == [(86_000, "2026-10-06")]


async def test_title_is_localized_and_backdated_records_do_not_move_odometer(
    client: AsyncClient,
) -> None:
    french = await register_user(client, preferred_language="fr")
    vehicle = await create_vehicle(client, french, current_mileage=90_000)
    record = await create_maintenance(client, french, vehicle["id"], mileage=70_000)
    assert record["title"] == "Vidange"
    assert record["maintenance_type"]["name"] == "Vidange"
    vehicle_now = data(await client.get(f"{API}/vehicles/{vehicle['id']}", headers=french.headers))
    assert vehicle_now["current_mileage"] == 90_000


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"service_date": "2027-01-01"}, "service_date"),
        ({"cost": "-1"}, "cost"),
        ({"mileage": -5}, "mileage"),
        ({"kind": "upgrade"}, "kind"),
        ({"garage_id": "01a11111-0000-7000-8000-000000000000"}, "garage_id"),
        ({"maintenance_type_id": "01a11111-0000-7000-8000-000000000000"}, "maintenance_type_id"),
    ],
)
async def test_validation(
    client: AsyncClient,
    user: AuthenticatedUser,
    vehicle: dict[str, Any],
    payload: dict[str, Any],
    field: str,
) -> None:
    body = {
        "maintenance_type_id": await maintenance_type_id(client, user, "oil_change"),
        "service_date": "2026-09-01",
        **payload,
    }
    response = await client.post(records_url(vehicle), headers=user.headers, json=body)
    assert field in error(response, 422, "VALIDATION_ERROR")["fields"]


async def test_cannot_use_another_users_garage_or_custom_type(
    client: AsyncClient,
    user: AuthenticatedUser,
    other_user: AuthenticatedUser,
    vehicle: dict[str, Any],
) -> None:
    foreign_garage = await create_garage(client, other_user)
    foreign_type = data(
        await client.post(
            f"{API}/maintenance-types", headers=other_user.headers, json={"name": "Secret"}
        ),
        201,
    )
    for field, value in (
        ("garage_id", foreign_garage["id"]),
        ("maintenance_type_id", foreign_type["id"]),
    ):
        body = {
            "maintenance_type_id": await maintenance_type_id(client, user, "oil_change"),
            "service_date": "2026-09-01",
            field: value,
        }
        response = await client.post(records_url(vehicle), headers=user.headers, json=body)
        assert field in error(response, 422, "VALIDATION_ERROR")["fields"]


async def test_update_and_delete(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    record = await create_maintenance(client, user, vehicle["id"], cost="100.00")
    url = f"{records_url(vehicle)}/{record['id']}"
    updated = data(
        await client.patch(
            url,
            headers=user.headers,
            json={"kind": "repair", "title": "Leak fix", "cost": None, "labor_cost": "80"},
        )
    )
    assert (updated["kind"], updated["title"], updated["cost"]) == ("repair", "Leak fix", "80.00")
    error(
        await client.patch(url, headers=user.headers, json={"title": None}), 422, "VALIDATION_ERROR"
    )

    assert (await client.delete(url, headers=user.headers)).status_code == 204
    error(await client.get(url, headers=user.headers), 404, "NOT_FOUND")


async def test_custom_type_in_use_cannot_be_deleted(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    custom = data(
        await client.post(f"{API}/maintenance-types", headers=user.headers, json={"name": "DPF"}),
        201,
    )
    await client.post(
        records_url(vehicle),
        headers=user.headers,
        json={"maintenance_type_id": custom["id"], "service_date": "2026-09-01"},
    )
    response = await client.delete(f"{API}/maintenance-types/{custom['id']}", headers=user.headers)
    error(response, 409, "TYPE_IN_USE")


async def test_filters_and_sorting(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    await create_maintenance(
        client, user, vehicle["id"], service_date="2025-01-10", cost="50", mileage=81_000
    )
    await create_maintenance(
        client,
        user,
        vehicle["id"],
        code="repair",
        kind="repair",
        title="Alternator",
        service_date="2026-02-01",
        cost="2100",
    )
    await create_maintenance(
        client, user, vehicle["id"], code="brake_pads", service_date="2026-05-01", cost="600"
    )

    async def ids(**params: Any) -> list[str]:
        body = (await client.get(records_url(vehicle), headers=user.headers, params=params)).json()
        return [r["title"] for r in body["data"]]

    assert await ids() == ["Brake pads", "Alternator", "Oil change"]
    assert await ids(kind="repair") == ["Alternator"]
    assert await ids(cost_min="500", sort="cost") == ["Brake pads", "Alternator"]
    assert await ids(date_from="2026-01-01", date_to="2026-03-01") == ["Alternator"]
    assert await ids(q="alter") == ["Alternator"]
    assert await ids(mileage_max=81_000) == ["Oil change"]


async def test_global_listing_spans_accessible_vehicles(
    client: AsyncClient,
    db_session: AsyncSession,
    user: AuthenticatedUser,
    other_user: AuthenticatedUser,
    vehicle: dict[str, Any],
) -> None:
    second = await create_vehicle(client, user, brand="Renault")
    foreign = await create_vehicle(client, other_user)
    await create_maintenance(client, user, vehicle["id"])
    await create_maintenance(client, user, second["id"])
    await create_maintenance(client, other_user, foreign["id"])

    body = (await client.get(f"{API}/maintenance", headers=user.headers)).json()
    assert body["meta"]["total"] == 2
    only_second = (
        await client.get(
            f"{API}/maintenance", headers=user.headers, params={"vehicle_id": second["id"]}
        )
    ).json()
    assert [r["vehicle_id"] for r in only_second["data"]] == [second["id"]]
    # Asking for a foreign vehicle simply yields nothing.
    foreign_query = (
        await client.get(
            f"{API}/maintenance", headers=user.headers, params={"vehicle_id": foreign["id"]}
        )
    ).json()
    assert foreign_query["meta"]["total"] == 0

    await share_vehicle_in_db(db_session, foreign["id"], user.id, "viewer")
    assert (await client.get(f"{API}/maintenance", headers=user.headers)).json()["meta"][
        "total"
    ] == 3


async def test_record_of_another_vehicle_is_not_reachable(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    other_vehicle = await create_vehicle(client, user)
    record = await create_maintenance(client, user, other_vehicle["id"])
    error(
        await client.get(f"{records_url(vehicle)}/{record['id']}", headers=user.headers),
        404,
        "NOT_FOUND",
    )


async def test_viewer_cannot_write(
    client: AsyncClient,
    db_session: AsyncSession,
    user: AuthenticatedUser,
    other_user: AuthenticatedUser,
    vehicle: dict[str, Any],
) -> None:
    record = await create_maintenance(client, user, vehicle["id"])
    await share_vehicle_in_db(db_session, vehicle["id"], other_user.id, "viewer")
    assert (await client.get(records_url(vehicle), headers=other_user.headers)).status_code == 200
    error(
        await client.delete(f"{records_url(vehicle)}/{record['id']}", headers=other_user.headers),
        403,
        "FORBIDDEN",
    )
