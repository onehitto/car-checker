"""Vehicles and vehicle sharing."""

import uuid
from datetime import date
from decimal import Decimal
from enum import StrEnum

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel, StrEnumType, enum_check
from app.modules.users.models import User


class FuelType(StrEnum):
    PETROL = "petrol"
    DIESEL = "diesel"
    ELECTRIC = "electric"
    HYBRID = "hybrid"
    PLUG_IN_HYBRID = "plug_in_hybrid"
    LPG = "lpg"
    CNG = "cng"
    HYDROGEN = "hydrogen"
    OTHER = "other"


class TransmissionType(StrEnum):
    MANUAL = "manual"
    AUTOMATIC = "automatic"
    SEMI_AUTOMATIC = "semi_automatic"
    CVT = "cvt"
    DUAL_CLUTCH = "dual_clutch"
    OTHER = "other"


class VehicleStatus(StrEnum):
    ACTIVE = "active"
    SOLD = "sold"
    ARCHIVED = "archived"


class VehicleRole(StrEnum):
    """Effective role of a user on a vehicle, ordered viewer < editor < owner."""

    VIEWER = "viewer"
    EDITOR = "editor"
    OWNER = "owner"

    @property
    def rank(self) -> int:
        return _ROLE_RANK[self]

    def allows(self, required: "VehicleRole") -> bool:
        return self.rank >= required.rank


_ROLE_RANK = {VehicleRole.VIEWER: 1, VehicleRole.EDITOR: 2, VehicleRole.OWNER: 3}


class SharedRole(StrEnum):
    """Roles that can be granted through sharing (ownership lives on vehicles.owner_id)."""

    EDITOR = "editor"
    VIEWER = "viewer"


class Vehicle(BaseModel):
    __tablename__ = "vehicles"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    nickname: Mapped[str | None] = mapped_column(sa.String(100))
    brand: Mapped[str] = mapped_column(sa.String(64))
    model: Mapped[str] = mapped_column(sa.String(64))
    trim: Mapped[str | None] = mapped_column(sa.String(64))
    year: Mapped[int] = mapped_column(sa.SmallInteger)
    license_plate: Mapped[str | None] = mapped_column(sa.String(20), index=True)
    vin: Mapped[str | None] = mapped_column(sa.String(32))
    fuel_type: Mapped[FuelType] = mapped_column(StrEnumType(FuelType))
    transmission_type: Mapped[TransmissionType | None] = mapped_column(
        StrEnumType(TransmissionType)
    )
    engine: Mapped[str | None] = mapped_column(sa.String(64))
    engine_displacement_cc: Mapped[int | None]
    horsepower: Mapped[int | None] = mapped_column(sa.SmallInteger)
    color: Mapped[str | None] = mapped_column(sa.String(32))
    purchase_date: Mapped[date | None]
    purchase_price: Mapped[Decimal | None]
    currency: Mapped[str] = mapped_column(sa.CHAR(3))
    initial_mileage: Mapped[int] = mapped_column(default=0, server_default="0")
    current_mileage: Mapped[int] = mapped_column(default=0, server_default="0")
    status: Mapped[VehicleStatus] = mapped_column(
        StrEnumType(VehicleStatus),
        default=VehicleStatus.ACTIVE,
        server_default=VehicleStatus.ACTIVE.value,
    )
    notes: Mapped[str | None] = mapped_column(sa.Text)

    owner: Mapped[User] = relationship(lazy="raise")

    __table_args__ = (
        sa.CheckConstraint("year BETWEEN 1886 AND 2100", name="year_range"),
        sa.CheckConstraint("initial_mileage >= 0", name="initial_mileage_positive"),
        sa.CheckConstraint("current_mileage >= 0", name="current_mileage_positive"),
        sa.CheckConstraint("purchase_price >= 0", name="purchase_price_positive"),
        sa.CheckConstraint("engine_displacement_cc > 0", name="displacement_positive"),
        sa.CheckConstraint("horsepower > 0", name="horsepower_positive"),
        enum_check("fuel_type", FuelType),
        enum_check("transmission_type", TransmissionType),
        enum_check("status", VehicleStatus),
        sa.Index(
            "uq_vehicles_owner_id_vin",
            "owner_id",
            "vin",
            unique=True,
            postgresql_where=sa.text("vin IS NOT NULL"),
        ),
    )

    @property
    def display_name(self) -> str:
        return self.nickname or f"{self.brand} {self.model}"


class VehicleAccess(BaseModel):
    """A user with whom a vehicle is shared, and their role."""

    __tablename__ = "vehicle_access"

    vehicle_id: Mapped[uuid.UUID] = mapped_column(sa.ForeignKey("vehicles.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[SharedRole] = mapped_column(StrEnumType(SharedRole, length=10))
    granted_by_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.ForeignKey("users.id", ondelete="SET NULL")
    )

    vehicle: Mapped[Vehicle] = relationship(lazy="raise")
    user: Mapped[User] = relationship(lazy="raise", foreign_keys=[user_id])

    __table_args__ = (
        sa.UniqueConstraint("vehicle_id", "user_id"),
        enum_check("role", SharedRole),
    )
