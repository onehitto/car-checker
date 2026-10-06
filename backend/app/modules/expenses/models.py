"""Expenses: the single money ledger of a vehicle."""

import uuid
from datetime import date
from decimal import Decimal
from enum import StrEnum

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, column_property, mapped_column, relationship

from app.db.base import BaseModel, StrEnumType, enum_check
from app.modules.maintenance.models import MaintenanceRecord
from app.modules.parts.models import PartReplacement
from app.modules.vehicles.models import Vehicle


class ExpenseCategory(StrEnum):
    MAINTENANCE = "maintenance"
    REPAIRS = "repairs"
    PARTS = "parts"
    FUEL = "fuel"
    INSURANCE = "insurance"
    TAXES = "taxes"
    PARKING = "parking"
    TOLLS = "tolls"
    FINES = "fines"
    WASHING = "washing"
    INSPECTION = "inspection"
    REGISTRATION = "registration"
    OTHER = "other"


class ExpenseSource(StrEnum):
    """Where an expense comes from. Linked expenses are maintained by their source record."""

    MANUAL = "manual"
    MAINTENANCE = "maintenance"
    PART = "part"


class Expense(BaseModel):
    __tablename__ = "expenses"

    vehicle_id: Mapped[uuid.UUID] = mapped_column(sa.ForeignKey("vehicles.id", ondelete="CASCADE"))
    category: Mapped[ExpenseCategory] = mapped_column(StrEnumType(ExpenseCategory))
    title: Mapped[str] = mapped_column(sa.String(200))
    amount: Mapped[Decimal]
    expense_date: Mapped[date]
    mileage: Mapped[int | None]
    vendor: Mapped[str | None] = mapped_column(sa.String(120))
    maintenance_record_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.ForeignKey("maintenance_records.id", ondelete="CASCADE"), unique=True
    )
    part_replacement_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.ForeignKey("part_replacements.id", ondelete="CASCADE"), unique=True
    )
    notes: Mapped[str | None] = mapped_column(sa.Text)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.ForeignKey("users.id", ondelete="SET NULL")
    )

    # Amounts are expressed in the vehicle's currency.
    currency: Mapped[str] = column_property(
        sa.select(Vehicle.currency).where(Vehicle.id == vehicle_id).scalar_subquery()
    )

    vehicle: Mapped[Vehicle] = relationship(lazy="raise")
    maintenance_record: Mapped[MaintenanceRecord | None] = relationship(lazy="raise")
    part_replacement: Mapped[PartReplacement | None] = relationship(lazy="raise")

    __table_args__ = (
        enum_check("category", ExpenseCategory),
        sa.CheckConstraint("amount >= 0", name="amount_positive"),
        sa.CheckConstraint("mileage >= 0", name="mileage_positive"),
        sa.CheckConstraint(
            "num_nonnulls(maintenance_record_id, part_replacement_id) <= 1", name="single_source"
        ),
        sa.Index(None, "vehicle_id", "expense_date"),
        sa.Index(None, "vehicle_id", "category"),
    )

    @property
    def source(self) -> ExpenseSource:
        if self.maintenance_record_id:
            return ExpenseSource.MAINTENANCE
        if self.part_replacement_id:
            return ExpenseSource.PART
        return ExpenseSource.MANUAL

    @property
    def source_id(self) -> uuid.UUID | None:
        return self.maintenance_record_id or self.part_replacement_id
