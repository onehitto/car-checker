"""Custom reminders and their alerts (clock: 2026-10-06)."""

from typing import Any

import pytest
from httpx import AsyncClient

from tests.helpers import API, AuthenticatedUser, create_vehicle, data, error


@pytest.fixture
async def vehicle(client: AsyncClient, user: AuthenticatedUser) -> dict[str, Any]:
    return await create_vehicle(client, user, current_mileage=80_000)


def url(vehicle: dict[str, Any]) -> str:
    return f"{API}/vehicles/{vehicle['id']}/reminders"


async def open_alerts(client: AsyncClient, user: AuthenticatedUser) -> list[dict[str, Any]]:
    response = await client.get(
        f"{API}/alerts", headers=user.headers, params={"status": ["active", "read"]}
    )
    return list(response.json()["data"])


async def test_reminder_lifecycle_and_alert(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    reminder = data(
        await client.post(
            url(vehicle),
            headers=user.headers,
            json={"title": "Renew parking badge", "due_date": "2026-10-10"},
        ),
        201,
    )
    assert (reminder["status"], reminder["remaining_days"]) == ("due", 4)
    [alert] = await open_alerts(client, user)
    assert (alert["alert_type"], alert["priority"], alert["title"]) == (
        "custom_reminder",
        "high",
        "Reminder due: Renew parking badge",
    )

    item = f"{url(vehicle)}/{reminder['id']}"
    done = data(await client.patch(item, headers=user.headers, json={"completed": True}))
    assert done["completed_at"] is not None
    assert await open_alerts(client, user) == []

    reopened = data(
        await client.patch(
            item, headers=user.headers, json={"completed": False, "due_date": "2027-01-01"}
        )
    )
    assert (reopened["completed_at"], reopened["status"]) == (None, "ok")
    assert (await client.delete(item, headers=user.headers)).status_code == 204


async def test_mileage_reminder_and_validation(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    far = data(
        await client.post(
            url(vehicle), headers=user.headers, json={"title": "Check tires", "due_mileage": 85_000}
        ),
        201,
    )
    assert (far["status"], far["remaining_km"]) == ("ok", 5_000)
    await client.post(
        f"{API}/vehicles/{vehicle['id']}/mileage", headers=user.headers, json={"mileage": 84_600}
    )
    [alert] = await open_alerts(client, user)
    assert alert["priority"] == "medium"

    error(
        await client.post(url(vehicle), headers=user.headers, json={"title": "x"}),
        422,
        "VALIDATION_ERROR",
    )
    cleared = await client.patch(
        f"{url(vehicle)}/{far['id']}", headers=user.headers, json={"due_mileage": None}
    )
    assert "due_date" in error(cleared, 422, "VALIDATION_ERROR")["fields"]

    listed = data(await client.get(url(vehicle), headers=user.headers, params={"completed": False}))
    assert [r["id"] for r in listed] == [far["id"]]
