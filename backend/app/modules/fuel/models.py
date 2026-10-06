"""Fuel fill-ups."""

import uuid
from datetime import date
from decimal import Decimal
from enum import StrEnum

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import UNIT_PRICE, BaseModel, StrEnumType, enum_check
from app.modules.vehicles.models import Vehicle


class PumpFuel(StrEnum):
    PETROL = "petrol"
    DIESEL = "diesel"
    E85 = "e85"
    LPG = "lpg"
    CNG = "cng"
    HYDROGEN = "hydrogen"
    OTHER = "other"


class FuelRecord(BaseModel):
    __tablename__ = "fuel_records"

    vehicle_id: Mapped[uuid.UUID] = mapped_column(sa.ForeignKey("vehicles.id", ondelete="CASCADE"))
    fill_date: Mapped[date]
    mileage: Mapped[int]
    liters: Mapped[Decimal] = mapped_column(sa.Numeric(8, 3))
    price_per_liter: Mapped[Decimal | None] = mapped_column(UNIT_PRICE)
    total_price: Mapped[Decimal | None]
    full_tank: Mapped[bool] = mapped_column(default=True, server_default=sa.true())
    # The user skipped recording one or more fill-ups before this one.
    missed_previous: Mapped[bool] = mapped_column(default=False, server_default=sa.false())
    fuel_type: Mapped[PumpFuel | None] = mapped_column(StrEnumType(PumpFuel))
    gas_station: Mapped[str | None] = mapped_column(sa.String(120))
    notes: Mapped[str | None] = mapped_column(sa.Text)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.ForeignKey("users.id", ondelete="SET NULL")
    )

    vehicle: Mapped[Vehicle] = relationship(lazy="raise")

    __table_args__ = (
        enum_check("fuel_type", PumpFuel),
        sa.CheckConstraint("mileage >= 0", name="mileage_positive"),
        sa.CheckConstraint("liters > 0", name="liters_positive"),
        sa.CheckConstraint("price_per_liter >= 0", name="price_per_liter_positive"),
        sa.CheckConstraint("total_price >= 0", name="total_price_positive"),
        sa.Index(None, "vehicle_id", "mileage"),
        sa.Index(None, "vehicle_id", "fill_date"),
    )
