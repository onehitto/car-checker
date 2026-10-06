"""Alert generation end to end (clock: 2026-10-06 10:00 UTC)."""

from datetime import timedelta
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.clock import FixedClock
from app.modules.alerts.engine import sync_all_vehicles
from tests.helpers import (
    API,
    AuthenticatedUser,
    create_document,
    create_maintenance,
    create_part,
    create_vehicle,
    data,
    login,
    maintenance_type_id,
    register_user,
    share_vehicle_in_db,
)


async def alerts(
    client: AsyncClient, user: AuthenticatedUser, **params: Any
) -> list[dict[str, Any]]:
    response = await client.get(
        f"{API}/alerts", headers=user.headers, params={"limit": 100, **params}
    )
    return list(response.json()["data"])


async def open_alerts(client: AsyncClient, user: AuthenticatedUser) -> list[dict[str, Any]]:
    return await alerts(client, user, status=["active", "read"])


@pytest.fixture
async def vehicle(client: AsyncClient, user: AuthenticatedUser) -> dict[str, Any]:
    return await create_vehicle(client, user, initial_mileage=40_000, current_mileage=59_400)


async def add_schedule(
    client: AsyncClient,
    user: AuthenticatedUser,
    vehicle: dict[str, Any],
    code: str = "oil_change",
    **fields: Any,
) -> dict[str, Any]:
    payload = {"maintenance_type_id": await maintenance_type_id(client, user, code), **fields}
    return dict(
        data(
            await client.post(
                f"{API}/vehicles/{vehicle['id']}/maintenance-schedules",
                headers=user.headers,
                json=payload,
            ),
            201,
        )
    )


async def test_schedule_alert_lifecycle(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    await add_schedule(
        client, user, vehicle, last_service_date="2025-11-01", last_service_mileage=50_000
    )
    [alert] = await open_alerts(client, user)
    assert (alert["alert_type"], alert["priority"], alert["status"]) == (
        "maintenance_due",
        "medium",
        "active",
    )
    assert alert["title"] == "Oil change due soon"
    assert alert["message"] == "Oil change for Dacia Logan is due in 600 km or 26 days."
    assert (alert["trigger_date"], alert["trigger_mileage"]) == ("2026-11-01", 60_000)
    assert alert["template_key"] == "alert.maintenance.due_soon"

    # Driving past the deadline escalates: the medium alert is resolved, a critical one appears.
    await client.post(
        f"{API}/vehicles/{vehicle['id']}/mileage", headers=user.headers, json={"mileage": 60_450}
    )
    [critical] = await open_alerts(client, user)
    assert (critical["priority"], critical["title"]) == ("critical", "Oil change overdue")
    assert "450 km overdue" in critical["message"]
    resolved = await alerts(client, user, status="resolved")
    assert [a["id"] for a in resolved] == [alert["id"]]

    # Doing the oil change resolves everything.
    await create_maintenance(client, user, vehicle["id"], service_date="2026-10-06", mileage=60_450)
    assert await open_alerts(client, user) == []


async def test_dismissed_alert_is_not_recreated_until_escalation(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    await add_schedule(
        client, user, vehicle, last_service_date="2025-11-01", last_service_mileage=50_000
    )
    [alert] = await open_alerts(client, user)
    await client.patch(
        f"{API}/alerts/{alert['id']}", headers=user.headers, json={"status": "dismissed"}
    )

    await client.post(
        f"{API}/vehicles/{vehicle['id']}/mileage", headers=user.headers, json={"mileage": 59_500}
    )
    assert await open_alerts(client, user) == []  # same situation: stays dismissed

    await client.post(
        f"{API}/vehicles/{vehicle['id']}/mileage", headers=user.headers, json={"mileage": 59_800}
    )
    [escalated] = await open_alerts(client, user)  # within 300 km: "due"
    assert escalated["priority"] == "high"


async def test_document_reminder_steps_and_renewal(
    client: AsyncClient,
    user: AuthenticatedUser,
    vehicle: dict[str, Any],
    clock: FixedClock,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    document = await create_document(
        client, user, vehicle["id"], title="AXA", expiration_date="2026-10-20"
    )
    [first] = await open_alerts(client, user)
    assert (first["alert_type"], first["priority"], first["title"]) == (
        "insurance_expiration",
        "medium",
        "AXA expires in 14 days",
    )

    # One week later the worker moves to the 7-day step.
    clock.set(clock.now() + timedelta(days=7))
    await sync_all_vehicles(session_factory, clock)
    [second] = await open_alerts(client, user)
    assert (second["priority"], second["title"]) == ("high", "AXA expires in 7 days")

    await client.patch(
        f"{API}/vehicles/{vehicle['id']}/documents/{document['id']}",
        headers=user.headers,
        json={"expiration_date": "2027-10-20"},
    )
    assert await open_alerts(client, user) == []


async def test_part_lifetime_alert(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    part = await create_part(
        client, user, vehicle["id"], installed_mileage=20_000
    )  # 40 000 km life
    [alert] = await open_alerts(client, user)
    assert (alert["alert_type"], alert["source_id"], alert["priority"]) == (
        "part_lifetime",
        part["id"],
        "medium",
    )
    await client.delete(f"{API}/vehicles/{vehicle['id']}/parts/{part['id']}", headers=user.headers)
    assert await open_alerts(client, user) == []


async def test_stale_mileage_reminder(
    client: AsyncClient,
    user: AuthenticatedUser,
    vehicle: dict[str, Any],
    clock: FixedClock,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    clock.set(clock.now() + timedelta(days=31))
    await sync_all_vehicles(session_factory, clock)
    user = await login(client, user.email)  # the 30-day session expired meanwhile
    [reminder] = await open_alerts(client, user)
    assert (reminder["alert_type"], reminder["priority"]) == ("mileage_reminder", "info")

    await client.post(
        f"{API}/vehicles/{vehicle['id']}/mileage", headers=user.headers, json={"mileage": 61_000}
    )
    assert await open_alerts(client, user) == []


async def test_recipients_language_and_sharing(
    client: AsyncClient, db_session: AsyncSession, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    editor = await register_user(client, preferred_language="fr")
    viewer = await register_user(client)
    await share_vehicle_in_db(db_session, vehicle["id"], editor.id, "editor")
    await share_vehicle_in_db(db_session, vehicle["id"], viewer.id, "viewer")

    await add_schedule(
        client, user, vehicle, last_service_date="2025-11-01", last_service_mileage=50_000
    )
    assert len(await open_alerts(client, user)) == 1
    [french] = await open_alerts(client, editor)
    assert french["title"] == "Vidange bientôt nécessaire"
    assert await open_alerts(client, viewer) == []


async def test_archived_vehicle_has_no_open_alerts(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    await add_schedule(
        client, user, vehicle, last_service_date="2025-11-01", last_service_mileage=50_000
    )
    await client.patch(
        f"{API}/vehicles/{vehicle['id']}", headers=user.headers, json={"status": "sold"}
    )
    assert await open_alerts(client, user) == []


async def test_sync_is_idempotent(
    client: AsyncClient,
    user: AuthenticatedUser,
    vehicle: dict[str, Any],
    clock: FixedClock,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await add_schedule(
        client, user, vehicle, last_service_date="2025-11-01", last_service_mileage=50_000
    )
    first = await sync_all_vehicles(session_factory, clock)
    second = await sync_all_vehicles(session_factory, clock)
    assert (first.created, first.resolved, second.created, second.resolved) == ([], 0, [], 0)
    assert len(await alerts(client, user)) == 1
