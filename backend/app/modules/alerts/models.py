"""Alerts: the in-app notification inbox of each user."""

import uuid
from datetime import date, datetime
from enum import StrEnum
from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel, StrEnumType, enum_check
from app.modules.users.models import User
from app.modules.vehicles.models import Vehicle


class AlertType(StrEnum):
    MAINTENANCE_DUE = "maintenance_due"
    DOCUMENT_EXPIRATION = "document_expiration"
    INSURANCE_EXPIRATION = "insurance_expiration"
    INSPECTION_DUE = "inspection_due"
    PART_LIFETIME = "part_lifetime"
    MILEAGE_REMINDER = "mileage_reminder"
    CUSTOM_REMINDER = "custom_reminder"
    SYSTEM = "system"


class AlertPriority(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @property
    def rank(self) -> int:
        return list(AlertPriority).index(self)


class AlertStatus(StrEnum):
    ACTIVE = "active"
    READ = "read"
    DISMISSED = "dismissed"
    RESOLVED = "resolved"


OPEN_STATUSES = (AlertStatus.ACTIVE, AlertStatus.READ)


class AlertSource(StrEnum):
    """Kind of record an alert is about (alerts of these sources are managed by the engine)."""

    MAINTENANCE_SCHEDULE = "maintenance_schedule"
    VEHICLE_DOCUMENT = "vehicle_document"
    PART_REPLACEMENT = "part_replacement"
    VEHICLE = "vehicle"
    REMINDER = "reminder"


class Alert(BaseModel):
    __tablename__ = "alerts"

    user_id: Mapped[uuid.UUID] = mapped_column(sa.ForeignKey("users.id", ondelete="CASCADE"))
    vehicle_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.ForeignKey("vehicles.id", ondelete="CASCADE")
    )
    alert_type: Mapped[AlertType] = mapped_column(StrEnumType(AlertType, length=30))
    source_type: Mapped[AlertSource | None] = mapped_column(StrEnumType(AlertSource, length=30))
    source_id: Mapped[uuid.UUID | None]
    # Identifies the situation (source + deadline + severity): makes generation idempotent.
    dedup_key: Mapped[str] = mapped_column(sa.String(200))
    title: Mapped[str] = mapped_column(sa.String(200))
    message: Mapped[str] = mapped_column(sa.Text)
    template_key: Mapped[str | None] = mapped_column(sa.String(100))
    template_params: Mapped[dict[str, Any]] = mapped_column(
        default=dict, server_default=sa.text("'{}'::jsonb")
    )
    priority: Mapped[AlertPriority] = mapped_column(StrEnumType(AlertPriority, length=10))
    status: Mapped[AlertStatus] = mapped_column(
        StrEnumType(AlertStatus, length=10),
        default=AlertStatus.ACTIVE,
        server_default=AlertStatus.ACTIVE.value,
    )
    trigger_date: Mapped[date | None]
    trigger_mileage: Mapped[int | None]
    read_at: Mapped[datetime | None]
    dismissed_at: Mapped[datetime | None]
    resolved_at: Mapped[datetime | None]

    user: Mapped[User] = relationship(lazy="raise")
    vehicle: Mapped[Vehicle | None] = relationship(lazy="raise")

    __table_args__ = (
        sa.UniqueConstraint("user_id", "dedup_key"),
        enum_check("alert_type", AlertType),
        enum_check("source_type", AlertSource),
        enum_check("priority", AlertPriority),
        enum_check("status", AlertStatus),
        sa.Index(None, "user_id", "status", "created_at"),
        sa.Index(None, "vehicle_id", "status"),
        sa.Index(None, "source_type", "source_id"),
    )
