"""Odometer readings."""

import uuid
from datetime import date
from enum import StrEnum

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel, StrEnumType, enum_check
from app.modules.vehicles.models import Vehicle


class MileageSource(StrEnum):
    INITIAL = "initial"
    MANUAL = "manual"
    MAINTENANCE = "maintenance"
    FUEL = "fuel"
    PART = "part"
    TIRE = "tire"
    OBD = "obd"
    IMPORT = "import"


class MileageEntry(BaseModel):
    __tablename__ = "mileage_history"

    vehicle_id: Mapped[uuid.UUID] = mapped_column(sa.ForeignKey("vehicles.id", ondelete="CASCADE"))
    mileage: Mapped[int]
    recorded_on: Mapped[date]
    source: Mapped[MileageSource] = mapped_column(StrEnumType(MileageSource))
    notes: Mapped[str | None] = mapped_column(sa.Text)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.ForeignKey("users.id", ondelete="SET NULL")
    )

    vehicle: Mapped[Vehicle] = relationship(lazy="raise")

    __table_args__ = (
        sa.CheckConstraint("mileage >= 0", name="mileage_positive"),
        enum_check("source", MileageSource),
        sa.Index(None, "vehicle_id", "recorded_on"),
    )
