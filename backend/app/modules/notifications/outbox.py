"""Queue notification deliveries for newly created alerts (outbox pattern).

Deliveries are inserted in the same transaction as their alerts; the dispatcher job sends
them later, so a slow e-mail provider never slows down an API request.
"""

import uuid
from collections import defaultdict
from collections.abc import Sequence
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ids import uuid7
from app.db.base import utc_now
from app.modules.alerts.models import AlertPriority, AlertType
from app.modules.notifications.models import (
    DeliveryStatus,
    NotificationDelivery,
    NotificationPreference,
)
from app.modules.notifications.preferences import (
    EXTERNAL_CHANNELS,
    StoredPreference,
    resolve_rule,
)


class NewAlert(Protocol):
    @property
    def id(self) -> uuid.UUID: ...

    @property
    def user_id(self) -> uuid.UUID: ...

    @property
    def priority(self) -> AlertPriority: ...

    @property
    def alert_type(self) -> AlertType: ...


async def load_preferences(
    session: AsyncSession, user_ids: set[uuid.UUID]
) -> dict[uuid.UUID, list[StoredPreference]]:
    result: dict[uuid.UUID, list[StoredPreference]] = defaultdict(list)
    rows = await session.scalars(
        select(NotificationPreference).where(NotificationPreference.user_id.in_(user_ids))
    )
    for row in rows:
        result[row.user_id].append(
            StoredPreference(row.channel, row.alert_type, row.enabled, row.min_priority)
        )
    return result


async def enqueue_deliveries(session: AsyncSession, alerts: Sequence[NewAlert]) -> int:
    """Insert one pending delivery per external channel the recipient wants (no commit)."""
    if not alerts:
        return 0
    preferences = await load_preferences(session, {alert.user_id for alert in alerts})
    now = utc_now()
    rows = [
        {
            "id": uuid7(),
            "alert_id": alert.id,
            "user_id": alert.user_id,
            "channel": channel,
            "status": DeliveryStatus.PENDING,
            "attempts": 0,
            "created_at": now,
            "updated_at": now,
        }
        for alert in alerts
        for channel in EXTERNAL_CHANNELS
        if resolve_rule(preferences[alert.user_id], channel, alert.alert_type).accepts(
            alert.priority
        )
    ]
    if rows:
        await session.execute(
            insert(NotificationDelivery)
            .values(rows)
            .on_conflict_do_nothing(
                index_elements=[NotificationDelivery.alert_id, NotificationDelivery.channel]
            )
        )
    return len(rows)
