"""Notification preference use cases."""

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notifications.models import (
    ALL_ALERT_TYPES,
    NotificationChannel,
    NotificationPreference,
)
from app.modules.notifications.preferences import DEFAULT_RULES
from app.modules.notifications.schemas import PreferenceResponse, PreferencesUpdate


class PreferenceService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def effective(self, user_id: uuid.UUID) -> list[PreferenceResponse]:
        """The general rule of every channel (stored or default), then per-type overrides."""
        stored = (
            await self.session.scalars(
                select(NotificationPreference).where(NotificationPreference.user_id == user_id)
            )
        ).all()
        general = {p.channel: p for p in stored if p.alert_type == ALL_ALERT_TYPES}
        result = []
        for channel in NotificationChannel:
            preference = general.get(channel)
            rule = DEFAULT_RULES[channel]
            result.append(
                PreferenceResponse(
                    channel=channel,
                    alert_type=ALL_ALERT_TYPES,
                    enabled=preference.enabled if preference else rule.enabled,
                    min_priority=preference.min_priority if preference else rule.min_priority,
                    is_default=preference is None,
                )
            )
        result.extend(
            PreferenceResponse(
                channel=p.channel,
                alert_type=p.alert_type,
                enabled=p.enabled,
                min_priority=p.min_priority,
                is_default=False,
            )
            for p in sorted(stored, key=lambda p: (p.channel, p.alert_type))
            if p.alert_type != ALL_ALERT_TYPES
        )
        return result

    async def replace(
        self, user_id: uuid.UUID, data: PreferencesUpdate
    ) -> list[PreferenceResponse]:
        await self.session.execute(
            delete(NotificationPreference).where(NotificationPreference.user_id == user_id)
        )
        self.session.add_all(
            NotificationPreference(user_id=user_id, **item.model_dump())
            for item in data.preferences
        )
        await self.session.commit()
        return await self.effective(user_id)
