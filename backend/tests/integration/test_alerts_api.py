"""Alert inbox endpoints (alerts are inserted directly; generation is tested separately)."""

import uuid
from typing import Any

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.alerts.models import Alert, AlertPriority, AlertType
from tests.helpers import API, AuthenticatedUser, create_vehicle, data, error


async def add_alert(
    session: AsyncSession,
    user: AuthenticatedUser,
    *,
    vehicle_id: str | None = None,
    priority: AlertPriority = AlertPriority.MEDIUM,
    alert_type: AlertType = AlertType.SYSTEM,
) -> str:
    alert = Alert(
        user_id=uuid.UUID(user.id),
        vehicle_id=uuid.UUID(vehicle_id) if vehicle_id else None,
        alert_type=alert_type,
        dedup_key=f"test:{uuid.uuid4()}",
        title=f"{priority.value} alert",
        message="Message",
        priority=priority,
    )
    session.add(alert)
    await session.commit()
    return str(alert.id)


async def titles(client: AsyncClient, user: AuthenticatedUser, **params: Any) -> list[str]:
    body = (await client.get(f"{API}/alerts", headers=user.headers, params=params)).json()
    return [a["title"] for a in body["data"]]


async def test_list_filter_and_sort(
    client: AsyncClient, db_session: AsyncSession, user: AuthenticatedUser
) -> None:
    for priority in (AlertPriority.LOW, AlertPriority.CRITICAL, AlertPriority.MEDIUM):
        await add_alert(db_session, user, priority=priority)
    assert await titles(client, user, sort="-priority") == [
        "critical alert",
        "medium alert",
        "low alert",
    ]
    assert await titles(client, user, priority=["low", "critical"], sort="priority") == [
        "low alert",
        "critical alert",
    ]
    assert await titles(client, user, alert_type="maintenance_due") == []


async def test_status_transitions(
    client: AsyncClient, db_session: AsyncSession, user: AuthenticatedUser
) -> None:
    alert_id = await add_alert(db_session, user)
    item = f"{API}/alerts/{alert_id}"

    read = data(await client.patch(item, headers=user.headers, json={"status": "read"}))
    assert read["status"] == "read" and read["read_at"] is not None
    unread = data(await client.patch(item, headers=user.headers, json={"status": "active"}))
    assert unread["read_at"] is None
    dismissed = data(await client.patch(item, headers=user.headers, json={"status": "dismissed"}))
    assert dismissed["dismissed_at"] is not None
    invalid = await client.patch(item, headers=user.headers, json={"status": "deleted"})
    assert "status" in error(invalid, 422, "VALIDATION_ERROR")["fields"]


async def test_summary_and_read_all(
    client: AsyncClient, db_session: AsyncSession, user: AuthenticatedUser
) -> None:
    vehicle = await create_vehicle(client, user)
    await add_alert(db_session, user, priority=AlertPriority.HIGH, vehicle_id=vehicle["id"])
    await add_alert(db_session, user, priority=AlertPriority.HIGH)
    dismissed = await add_alert(db_session, user, priority=AlertPriority.LOW)
    await client.patch(
        f"{API}/alerts/{dismissed}", headers=user.headers, json={"status": "dismissed"}
    )

    summary = data(await client.get(f"{API}/alerts/summary", headers=user.headers))
    assert (summary["open"], summary["unread"], summary["by_priority"]["high"]) == (2, 2, 2)

    updated = data(
        await client.post(
            f"{API}/alerts/read-all", headers=user.headers, params={"vehicle_id": vehicle["id"]}
        )
    )
    assert updated == {"updated": 1}
    summary = data(await client.get(f"{API}/alerts/summary", headers=user.headers))
    assert (summary["open"], summary["unread"]) == (2, 1)

    vehicle_alerts = (
        await client.get(f"{API}/vehicles/{vehicle['id']}/alerts", headers=user.headers)
    ).json()
    assert vehicle_alerts["meta"]["total"] == 1


async def test_alerts_are_private(
    client: AsyncClient,
    db_session: AsyncSession,
    user: AuthenticatedUser,
    other_user: AuthenticatedUser,
) -> None:
    alert_id = await add_alert(db_session, user)
    assert await titles(client, other_user) == []
    error(
        await client.get(f"{API}/alerts/{alert_id}", headers=other_user.headers), 404, "NOT_FOUND"
    )
    error(
        await client.patch(
            f"{API}/alerts/{alert_id}", headers=other_user.headers, json={"status": "read"}
        ),
        404,
        "NOT_FOUND",
    )
