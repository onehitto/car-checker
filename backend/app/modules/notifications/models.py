"""Notification preferences and the delivery outbox for external channels."""

import uuid
from datetime import datetime
from enum import StrEnum

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel, StrEnumType, enum_check
from app.modules.alerts.models import Alert, AlertPriority
from app.modules.users.models import User

ALL_ALERT_TYPES = "all"


class NotificationChannel(StrEnum):
    IN_APP = "in_app"
    EMAIL = "email"
    PUSH = "push"
    SMS = "sms"


class DeliveryStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    SKIPPED = "skipped"


class NotificationPreference(BaseModel):
    """Per channel and alert type (or `all`): enabled and minimum priority."""

    __tablename__ = "notification_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(sa.ForeignKey("users.id", ondelete="CASCADE"))
    channel: Mapped[NotificationChannel] = mapped_column(
        StrEnumType(NotificationChannel, length=10)
    )
    alert_type: Mapped[str] = mapped_column(
        sa.String(30), default=ALL_ALERT_TYPES, server_default=ALL_ALERT_TYPES
    )
    enabled: Mapped[bool] = mapped_column(default=True, server_default=sa.true())
    min_priority: Mapped[AlertPriority] = mapped_column(
        StrEnumType(AlertPriority, length=10),
        default=AlertPriority.LOW,
        server_default=AlertPriority.LOW.value,
    )

    user: Mapped[User] = relationship(lazy="raise")

    __table_args__ = (
        sa.UniqueConstraint("user_id", "channel", "alert_type"),
        enum_check("channel", NotificationChannel),
        enum_check("min_priority", AlertPriority),
    )


class NotificationDelivery(BaseModel):
    """One alert to send through one external channel (the in-app channel is the alert)."""

    __tablename__ = "notification_deliveries"

    alert_id: Mapped[uuid.UUID] = mapped_column(sa.ForeignKey("alerts.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        StrEnumType(NotificationChannel, length=10)
    )
    status: Mapped[DeliveryStatus] = mapped_column(
        StrEnumType(DeliveryStatus, length=10),
        default=DeliveryStatus.PENDING,
        server_default=DeliveryStatus.PENDING.value,
    )
    attempts: Mapped[int] = mapped_column(sa.SmallInteger, default=0, server_default="0")
    last_error: Mapped[str | None] = mapped_column(sa.String(500))
    sent_at: Mapped[datetime | None]

    alert: Mapped[Alert] = relationship(lazy="raise")
    user: Mapped[User] = relationship(lazy="raise")

    __table_args__ = (
        sa.UniqueConstraint("alert_id", "channel"),
        enum_check("channel", NotificationChannel),
        enum_check("status", DeliveryStatus),
        sa.Index(
            "ix_notification_deliveries_pending",
            "created_at",
            postgresql_where=sa.text("status = 'pending'"),
        ),
    )
