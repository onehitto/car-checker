"""Tires: mounting, rotation, events and history."""

from typing import Any

import pytest
from httpx import AsyncClient

from tests.helpers import API, AuthenticatedUser, create_vehicle, data, error


@pytest.fixture
async def vehicle(client: AsyncClient, user: AuthenticatedUser) -> dict[str, Any]:
    return await create_vehicle(client, user, current_mileage=80_000)


def url(vehicle: dict[str, Any]) -> str:
    return f"{API}/vehicles/{vehicle['id']}/tires"


async def add_tire(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any], **fields: Any
) -> dict[str, Any]:
    payload = {"brand": "Michelin", "size": "205/55 R16 91V", "season": "summer", **fields}
    return dict(data(await client.post(url(vehicle), headers=user.headers, json=payload), 201))


async def mounted(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> dict[str, str]:
    tires = data(await client.get(url(vehicle), headers=user.headers, params={"status": "mounted"}))
    return {t["position"]: t["id"] for t in tires}


async def test_mount_and_store(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    front = await add_tire(client, user, vehicle, position="front_left", installed_mileage=80_000)
    assert (front["status"], front["installed_date"]) == ("mounted", "2026-10-06")
    winter = await add_tire(client, user, vehicle, season="winter")
    assert (winter["status"], winter["position"]) == ("stored", None)

    events = data(await client.get(f"{url(vehicle)}/{front['id']}/events", headers=user.headers))
    assert [(e["event_type"], e["to_position"]) for e in events] == [("installed", "front_left")]

    taken = await client.post(
        url(vehicle),
        headers=user.headers,
        json={"brand": "X", "size": "205/55 R16", "season": "summer", "position": "front_left"},
    )
    error(taken, 409, "TIRE_POSITION_TAKEN")


async def test_rotation_swaps_positions_atomically(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    positions = ["front_left", "front_right", "rear_left", "rear_right"]
    ids = {p: (await add_tire(client, user, vehicle, position=p))["id"] for p in positions}

    rotated = data(
        await client.post(
            f"{url(vehicle)}/rotations",
            headers=user.headers,
            json={
                "rotation_date": "2026-10-06",
                "mileage": 81_000,
                "moves": [
                    {"tire_id": ids["front_left"], "to_position": "rear_left"},
                    {"tire_id": ids["rear_left"], "to_position": "front_left"},
                    {"tire_id": ids["front_right"], "to_position": "rear_right"},
                    {"tire_id": ids["rear_right"], "to_position": "front_right"},
                ],
            },
        )
    )
    assert len(rotated) == 4
    assert await mounted(client, user, vehicle) == {
        "rear_left": ids["front_left"],
        "front_left": ids["rear_left"],
        "rear_right": ids["front_right"],
        "front_right": ids["rear_right"],
    }
    events = data(
        await client.get(f"{url(vehicle)}/{ids['front_left']}/events", headers=user.headers)
    )
    assert (events[0]["event_type"], events[0]["from_position"], events[0]["to_position"]) == (
        "rotated",
        "front_left",
        "rear_left",
    )
    assert (
        data(await client.get(f"{API}/vehicles/{vehicle['id']}", headers=user.headers))[
            "current_mileage"
        ]
        == 81_000
    )


async def test_rotation_rules(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    fl = await add_tire(client, user, vehicle, position="front_left")
    fr = await add_tire(client, user, vehicle, position="front_right")
    stored = await add_tire(client, user, vehicle)
    rotation = f"{url(vehicle)}/rotations"

    clash = await client.post(
        rotation,
        headers=user.headers,
        json={
            "rotation_date": "2026-10-06",
            "moves": [{"tire_id": fl["id"], "to_position": "front_right"}],
        },
    )
    error(clash, 422, "BUSINESS_RULE_VIOLATION")
    duplicate = await client.post(
        rotation,
        headers=user.headers,
        json={
            "rotation_date": "2026-10-06",
            "moves": [
                {"tire_id": fl["id"], "to_position": "spare"},
                {"tire_id": fr["id"], "to_position": "spare"},
            ],
        },
    )
    error(duplicate, 422, "VALIDATION_ERROR")
    not_mounted = await client.post(
        rotation,
        headers=user.headers,
        json={
            "rotation_date": "2026-10-06",
            "moves": [{"tire_id": stored["id"], "to_position": "spare"}],
        },
    )
    error(not_mounted, 422, "BUSINESS_RULE_VIOLATION")
    assert await mounted(client, user, vehicle) == {"front_left": fl["id"], "front_right": fr["id"]}


async def test_events_change_state(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    summer = await add_tire(client, user, vehicle, position="front_left")
    winter = await add_tire(client, user, vehicle, season="winter")
    events = f"{url(vehicle)}"

    removed = await client.post(
        f"{events}/{summer['id']}/events",
        headers=user.headers,
        json={"event_type": "removed", "event_date": "2026-10-06"},
    )
    assert data(removed, 201)["from_position"] == "front_left"
    installed = await client.post(
        f"{events}/{winter['id']}/events",
        headers=user.headers,
        json={
            "event_type": "installed",
            "event_date": "2026-10-06",
            "to_position": "front_left",
            "mileage": 80_100,
        },
    )
    data(installed, 201)
    assert await mounted(client, user, vehicle) == {"front_left": winter["id"]}

    inspected = await client.post(
        f"{events}/{winter['id']}/events",
        headers=user.headers,
        json={
            "event_type": "inspected",
            "event_date": "2026-10-06",
            "tread_depth_mm": "6.5",
            "condition": "good",
        },
    )
    data(inspected, 201)
    tire = data(await client.get(f"{events}/{winter['id']}", headers=user.headers))
    assert (tire["tread_depth_mm"], tire["condition"]) == ("6.5", "good")

    missing_position = await client.post(
        f"{events}/{summer['id']}/events",
        headers=user.headers,
        json={"event_type": "installed", "event_date": "2026-10-06"},
    )
    error(missing_position, 422, "VALIDATION_ERROR")
    discarded = await client.post(
        f"{events}/{summer['id']}/events",
        headers=user.headers,
        json={"event_type": "discarded", "event_date": "2026-10-06"},
    )
    data(discarded, 201)
    again = await client.post(
        f"{events}/{summer['id']}/events",
        headers=user.headers,
        json={"event_type": "installed", "event_date": "2026-10-06", "to_position": "spare"},
    )
    error(again, 422, "BUSINESS_RULE_VIOLATION")

    timeline = data(
        await client.get(
            f"{API}/vehicles/{vehicle['id']}/timeline",
            headers=user.headers,
            params={"type": "tire"},
        )
    )
    assert {e["subtype"] for e in timeline} == {"installed", "removed", "inspected", "discarded"}


async def test_update_and_delete(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    tire = await add_tire(client, user, vehicle, position="spare")
    item = f"{url(vehicle)}/{tire['id']}"
    updated = data(
        await client.patch(
            item, headers=user.headers, json={"dot_code": "DOT 2324", "price": "120.00"}
        )
    )
    assert (updated["dot_code"], updated["price"]) == ("DOT 2324", "120.00")
    position_patch = await client.patch(item, headers=user.headers, json={"position": "front_left"})
    assert "position" in error(position_patch, 422, "VALIDATION_ERROR")["fields"]
    assert (await client.delete(item, headers=user.headers)).status_code == 204
    error(await client.get(item, headers=user.headers), 404, "NOT_FOUND")
