"""Tires and their history (installation, rotations, inspections, removal)."""

import uuid
from datetime import date
from decimal import Decimal
from enum import StrEnum

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel, StrEnumType, enum_check
from app.modules.vehicles.models import Vehicle


class TireSeason(StrEnum):
    SUMMER = "summer"
    WINTER = "winter"
    ALL_SEASON = "all_season"


class TirePosition(StrEnum):
    FRONT_LEFT = "front_left"
    FRONT_RIGHT = "front_right"
    REAR_LEFT = "rear_left"
    REAR_RIGHT = "rear_right"
    SPARE = "spare"


class TireStatus(StrEnum):
    MOUNTED = "mounted"
    STORED = "stored"
    DISCARDED = "discarded"


class TireCondition(StrEnum):
    NEW = "new"
    GOOD = "good"
    FAIR = "fair"
    WORN = "worn"
    DAMAGED = "damaged"


class TireEventType(StrEnum):
    INSTALLED = "installed"
    ROTATED = "rotated"
    REMOVED = "removed"
    INSPECTED = "inspected"
    REPAIRED = "repaired"
    DISCARDED = "discarded"


TREAD_DEPTH = sa.Numeric(4, 1)


class Tire(BaseModel):
    __tablename__ = "tires"

    vehicle_id: Mapped[uuid.UUID] = mapped_column(sa.ForeignKey("vehicles.id", ondelete="CASCADE"))
    brand: Mapped[str] = mapped_column(sa.String(80))
    model: Mapped[str | None] = mapped_column(sa.String(80))
    size: Mapped[str] = mapped_column(sa.String(32))
    season: Mapped[TireSeason] = mapped_column(StrEnumType(TireSeason))
    dot_code: Mapped[str | None] = mapped_column(sa.String(20))
    position: Mapped[TirePosition | None] = mapped_column(StrEnumType(TirePosition))
    status: Mapped[TireStatus] = mapped_column(StrEnumType(TireStatus))
    condition: Mapped[TireCondition | None] = mapped_column(StrEnumType(TireCondition))
    purchase_date: Mapped[date | None]
    price: Mapped[Decimal | None]
    installed_date: Mapped[date | None]
    installed_mileage: Mapped[int | None]
    tread_depth_mm: Mapped[Decimal | None] = mapped_column(TREAD_DEPTH)
    pressure_notes: Mapped[str | None] = mapped_column(sa.String(200))
    notes: Mapped[str | None] = mapped_column(sa.Text)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.ForeignKey("users.id", ondelete="SET NULL")
    )

    vehicle: Mapped[Vehicle] = relationship(lazy="raise")

    __table_args__ = (
        enum_check("season", TireSeason),
        enum_check("position", TirePosition),
        enum_check("status", TireStatus),
        enum_check("condition", TireCondition),
        sa.CheckConstraint(
            "status <> 'mounted' OR position IS NOT NULL", name="mounted_tire_has_position"
        ),
        sa.CheckConstraint("price >= 0", name="price_positive"),
        sa.CheckConstraint("installed_mileage >= 0", name="installed_mileage_positive"),
        sa.CheckConstraint("tread_depth_mm >= 0", name="tread_depth_positive"),
        sa.Index(None, "vehicle_id"),
        # Two mounted tires can never share a position on the same vehicle.
        sa.Index(
            "uq_tires_mounted_position",
            "vehicle_id",
            "position",
            unique=True,
            postgresql_where=sa.text("status = 'mounted'"),
        ),
    )


class TireEvent(BaseModel):
    __tablename__ = "tire_events"

    tire_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("tires.id", ondelete="CASCADE"), index=True
    )
    # Denormalized for the vehicle timeline.
    vehicle_id: Mapped[uuid.UUID] = mapped_column(sa.ForeignKey("vehicles.id", ondelete="CASCADE"))
    event_type: Mapped[TireEventType] = mapped_column(StrEnumType(TireEventType))
    event_date: Mapped[date]
    mileage: Mapped[int | None]
    from_position: Mapped[TirePosition | None] = mapped_column(StrEnumType(TirePosition))
    to_position: Mapped[TirePosition | None] = mapped_column(StrEnumType(TirePosition))
    tread_depth_mm: Mapped[Decimal | None] = mapped_column(TREAD_DEPTH)
    notes: Mapped[str | None] = mapped_column(sa.Text)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.ForeignKey("users.id", ondelete="SET NULL")
    )

    tire: Mapped[Tire] = relationship(lazy="raise")
    vehicle: Mapped[Vehicle] = relationship(lazy="raise")

    __table_args__ = (
        enum_check("event_type", TireEventType),
        enum_check("from_position", TirePosition),
        enum_check("to_position", TirePosition),
        sa.CheckConstraint("mileage >= 0", name="mileage_positive"),
        sa.Index(None, "vehicle_id", "event_date"),
    )
