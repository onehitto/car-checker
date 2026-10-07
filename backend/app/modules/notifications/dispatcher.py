"""Send pending notification deliveries through their channel providers."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.clock import Clock
from app.core.config import Settings
from app.core.i18n import translate
from app.core.logging import get_logger
from app.modules.alerts.models import Alert, AlertStatus
from app.modules.notifications.email import EmailMessage, EmailSender
from app.modules.notifications.models import (
    DeliveryStatus,
    NotificationChannel,
    NotificationDelivery,
)
from app.modules.users.models import User

logger = get_logger(__name__)

MAX_ATTEMPTS = 5
BATCH_SIZE = 100


class ChannelUnavailableError(Exception):
    """The channel cannot deliver (no provider configured): the delivery is skipped."""


class ChannelProvider(Protocol):
    async def send(self, user: User, alert: Alert) -> None: ...


class EmailChannel:
    def __init__(self, sender: EmailSender, settings: Settings) -> None:
        self.sender = sender
        self.app_url = settings.frontend_url

    async def send(self, user: User, alert: Alert) -> None:
        language = user.preferred_language
        await self.sender.send(
            EmailMessage(
                to=user.email,
                subject=translate("email.alert.subject", language, title=alert.title),
                body=translate(
                    "email.alert.body",
                    language,
                    first_name=user.first_name,
                    message=alert.message,
                    app_url=self.app_url,
                ),
            )
        )


class UnconfiguredChannel:
    """Placeholder for channels without a provider yet (push: FCM/APNs, SMS: Twilio...)."""

    def __init__(self, channel: NotificationChannel) -> None:
        self.channel = channel

    async def send(self, user: User, alert: Alert) -> None:
        raise ChannelUnavailableError(f"No {self.channel.value} provider configured")


def build_providers(
    sender: EmailSender, settings: Settings
) -> dict[NotificationChannel, ChannelProvider]:
    return {
        NotificationChannel.EMAIL: EmailChannel(sender, settings),
        NotificationChannel.PUSH: UnconfiguredChannel(NotificationChannel.PUSH),
        NotificationChannel.SMS: UnconfiguredChannel(NotificationChannel.SMS),
    }


@dataclass(slots=True)
class DispatchResult:
    counts: dict[str, int] = field(
        default_factory=lambda: {status.value: 0 for status in DeliveryStatus}
    )

    def add(self, status: DeliveryStatus) -> None:
        self.counts[status.value] += 1


async def dispatch_pending(
    session_factory: async_sessionmaker[AsyncSession],
    providers: Mapping[NotificationChannel, ChannelProvider],
    clock: Clock,
    batch_size: int = BATCH_SIZE,
) -> DispatchResult:
    """Process one batch. Rows are locked with SKIP LOCKED so workers never send twice."""
    result = DispatchResult()
    async with session_factory() as session:
        rows = (
            await session.execute(
                select(NotificationDelivery, Alert, User)
                .join(Alert, Alert.id == NotificationDelivery.alert_id)
                .join(User, User.id == NotificationDelivery.user_id)
                .where(NotificationDelivery.status == DeliveryStatus.PENDING)
                .order_by(NotificationDelivery.created_at)
                .limit(batch_size)
                .with_for_update(of=NotificationDelivery, skip_locked=True)
            )
        ).all()
        for delivery, alert, user in rows:
            delivery.status = await _deliver(delivery, alert, user, providers, clock)
            result.add(delivery.status)
        await session.commit()
    return result


async def _deliver(
    delivery: NotificationDelivery,
    alert: Alert,
    user: User,
    providers: Mapping[NotificationChannel, ChannelProvider],
    clock: Clock,
) -> DeliveryStatus:
    if alert.status in (AlertStatus.DISMISSED, AlertStatus.RESOLVED) or not user.is_active:
        delivery.last_error = "alert_closed"
        return DeliveryStatus.SKIPPED
    provider = providers.get(delivery.channel)
    try:
        if provider is None:
            raise ChannelUnavailableError(f"No {delivery.channel.value} provider")
        await provider.send(user, alert)
    except ChannelUnavailableError as exc:
        delivery.last_error = str(exc)[:500]
        return DeliveryStatus.SKIPPED
    except Exception as exc:  # noqa: BLE001 - retried later, never crash the batch
        delivery.attempts += 1
        delivery.last_error = type(exc).__name__
        logger.warning(
            "notification_delivery_failed",
            channel=delivery.channel.value,
            attempts=delivery.attempts,
            error=type(exc).__name__,
        )
        return (
            DeliveryStatus.FAILED if delivery.attempts >= MAX_ATTEMPTS else DeliveryStatus.PENDING
        )
    delivery.attempts += 1
    delivery.sent_at = clock.now()
    delivery.last_error = None
    return DeliveryStatus.SENT
