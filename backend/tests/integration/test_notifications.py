"""Notification preferences, delivery outbox and dispatch."""

from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.clock import FixedClock
from app.core.config import Settings
from app.jobs.registry import JobContext
from app.jobs.tasks import dispatch_notifications
from app.modules.alerts.models import Alert, AlertPriority, AlertType
from app.modules.notifications.dispatcher import MAX_ATTEMPTS, dispatch_pending
from app.modules.notifications.email import MemoryEmailSender
from app.modules.notifications.models import NotificationChannel, NotificationDelivery
from app.modules.users.models import User
from tests.helpers import (
    API,
    AuthenticatedUser,
    create_vehicle,
    data,
    error,
    maintenance_type_id,
    register_user,
)

URL = f"{API}/users/me/notification-preferences"


async def overdue_schedule(client: AsyncClient, user: AuthenticatedUser) -> None:
    vehicle = await create_vehicle(client, user, initial_mileage=40_000, current_mileage=59_400)
    response = await client.post(
        f"{API}/vehicles/{vehicle['id']}/maintenance-schedules",
        headers=user.headers,
        json={
            "maintenance_type_id": await maintenance_type_id(client, user, "air_filter"),
            "interval_km": 15_000,
            "last_service_mileage": 40_000,
        },
    )
    assert response.status_code == 201


async def deliveries(session: AsyncSession, user: AuthenticatedUser) -> list[NotificationDelivery]:
    import uuid

    rows = await session.scalars(
        select(NotificationDelivery).where(NotificationDelivery.user_id == uuid.UUID(user.id))
    )
    return list(rows)


def context(
    session_factory: async_sessionmaker[AsyncSession],
    clock: FixedClock,
    settings: Settings,
    sender: Any,
) -> JobContext:
    return JobContext(
        session_factory=session_factory,
        clock=clock,
        settings=settings,
        extras={"email_sender": sender},
    )


async def test_default_and_replaced_preferences(
    client: AsyncClient, user: AuthenticatedUser
) -> None:
    defaults = data(await client.get(URL, headers=user.headers))
    assert [(p["channel"], p["enabled"], p["min_priority"], p["is_default"]) for p in defaults] == [
        ("in_app", True, "info", True),
        ("email", True, "high", True),
        ("push", False, "medium", True),
        ("sms", False, "critical", True),
    ]
    updated = data(
        await client.put(
            URL,
            headers=user.headers,
            json={
                "preferences": [
                    {"channel": "email", "enabled": True, "min_priority": "medium"},
                    {"channel": "email", "alert_type": "mileage_reminder", "enabled": False},
                ]
            },
        )
    )
    assert updated[1] == {
        "channel": "email",
        "alert_type": "all",
        "enabled": True,
        "min_priority": "medium",
        "is_default": False,
    }
    assert updated[-1]["alert_type"] == "mileage_reminder"

    bad_type = await client.put(
        URL,
        headers=user.headers,
        json={"preferences": [{"channel": "email", "alert_type": "spam"}]},
    )
    error(bad_type, 422, "VALIDATION_ERROR")
    duplicate = await client.put(
        URL, headers=user.headers, json={"preferences": [{"channel": "sms"}, {"channel": "sms"}]}
    )
    error(duplicate, 422, "VALIDATION_ERROR")


async def test_critical_alert_is_emailed_in_user_language(
    client: AsyncClient,
    db_session: AsyncSession,
    session_factory: async_sessionmaker[AsyncSession],
    clock: FixedClock,
    settings: Settings,
) -> None:
    owner = await register_user(client, preferred_language="fr", first_name="Amina")
    await client.put(
        URL, headers=owner.headers, json={"preferences": [{"channel": "push", "enabled": True}]}
    )
    await overdue_schedule(client, owner)

    pending = await deliveries(db_session, owner)
    assert sorted(d.channel.value for d in pending) == ["email", "push"]

    sender = MemoryEmailSender()
    counts = await dispatch_notifications(context(session_factory, clock, settings, sender))
    assert counts == {"pending": 0, "sent": 1, "failed": 0, "skipped": 1}
    [email] = sender.outbox
    assert email.to == owner.email
    assert email.subject == "[Car Checker] Remplacement du filtre à air en retard"
    assert email.body.startswith("Bonjour Amina")

    by_channel = {d.channel: d for d in await deliveries(db_session, owner)}
    await db_session.refresh(by_channel[NotificationChannel.PUSH])
    assert by_channel[NotificationChannel.PUSH].last_error == "No push provider configured"


async def test_medium_alerts_are_not_emailed_by_default(
    client: AsyncClient, db_session: AsyncSession, user: AuthenticatedUser
) -> None:
    vehicle = await create_vehicle(client, user, initial_mileage=40_000, current_mileage=59_400)
    await client.post(
        f"{API}/vehicles/{vehicle['id']}/maintenance-schedules",
        headers=user.headers,
        json={
            "maintenance_type_id": await maintenance_type_id(client, user, "oil_change"),
            "last_service_date": "2025-11-01",
            "last_service_mileage": 50_000,
        },
    )
    assert await deliveries(db_session, user) == []


async def test_failures_are_retried_then_marked_failed(
    db_session: AsyncSession,
    session_factory: async_sessionmaker[AsyncSession],
    clock: FixedClock,
    user: AuthenticatedUser,
) -> None:
    import uuid

    db_user = await db_session.get(User, uuid.UUID(user.id))
    assert db_user is not None
    alert = Alert(
        user_id=db_user.id,
        alert_type=AlertType.SYSTEM,
        dedup_key="test",
        title="T",
        message="M",
        priority=AlertPriority.HIGH,
    )
    db_session.add(alert)
    db_session.add(
        NotificationDelivery(
            alert_id=alert.id, user_id=db_user.id, channel=NotificationChannel.EMAIL
        )
    )
    await db_session.commit()

    class Broken:
        async def send(self, user: User, alert: Alert) -> None:
            raise ConnectionError("smtp down")

    providers = {NotificationChannel.EMAIL: Broken()}
    for attempt in range(1, MAX_ATTEMPTS + 1):
        result = await dispatch_pending(session_factory, providers, clock)  # type: ignore[arg-type]
        expected = "failed" if attempt == MAX_ATTEMPTS else "pending"
        assert result.counts[expected] == 1
    [delivery] = await deliveries(db_session, user)
    await db_session.refresh(delivery)
    assert (delivery.attempts, delivery.last_error) == (MAX_ATTEMPTS, "ConnectionError")


@pytest.mark.parametrize("status", ["dismissed", "resolved"])
async def test_closed_alerts_are_skipped(
    client: AsyncClient,
    db_session: AsyncSession,
    session_factory: async_sessionmaker[AsyncSession],
    clock: FixedClock,
    settings: Settings,
    user: AuthenticatedUser,
    status: str,
) -> None:
    await overdue_schedule(client, user)
    [alert] = data(await client.get(f"{API}/alerts", headers=user.headers))
    await client.patch(f"{API}/alerts/{alert['id']}", headers=user.headers, json={"status": status})
    sender = MemoryEmailSender()
    counts = await dispatch_notifications(context(session_factory, clock, settings, sender))
    assert counts["skipped"] == 1 and sender.outbox == []
