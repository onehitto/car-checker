"""Part catalog and part replacements."""

import uuid
from datetime import date
from decimal import Decimal
from enum import StrEnum

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel, StrEnumType, enum_check
from app.db.catalog import CatalogTypeMixin, catalog_table_args
from app.modules.garages.models import Garage
from app.modules.maintenance.models import MaintenanceRecord
from app.modules.vehicles.models import Vehicle


class PartCategory(StrEnum):
    ENGINE = "engine"
    FILTERS = "filters"
    BRAKES = "brakes"
    ELECTRICAL = "electrical"
    TIRES = "tires"
    SUSPENSION = "suspension"
    TRANSMISSION = "transmission"
    COOLING = "cooling"
    LIGHTING = "lighting"
    BODY = "body"
    OTHER = "other"


class PartType(CatalogTypeMixin, BaseModel):
    __tablename__ = "part_types"
    translation_prefix = "part_type"

    category: Mapped[PartCategory] = mapped_column(StrEnumType(PartCategory))
    default_lifetime_km: Mapped[int | None]
    default_lifetime_months: Mapped[int | None] = mapped_column(sa.SmallInteger)

    __table_args__ = (
        *catalog_table_args("part_types"),
        enum_check("category", PartCategory),
        sa.CheckConstraint("default_lifetime_km > 0", name="default_lifetime_km_positive"),
        sa.CheckConstraint("default_lifetime_months > 0", name="default_lifetime_months_positive"),
    )


class PartReplacement(BaseModel):
    """A part installed on a vehicle (and later removed when superseded)."""

    __tablename__ = "part_replacements"

    vehicle_id: Mapped[uuid.UUID] = mapped_column(sa.ForeignKey("vehicles.id", ondelete="CASCADE"))
    part_type_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("part_types.id", ondelete="RESTRICT"), index=True
    )
    maintenance_record_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.ForeignKey("maintenance_records.id", ondelete="SET NULL"), index=True
    )
    garage_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.ForeignKey("garages.id", ondelete="SET NULL"), index=True
    )
    part_name: Mapped[str] = mapped_column(sa.String(150))
    brand: Mapped[str | None] = mapped_column(sa.String(80))
    reference_number: Mapped[str | None] = mapped_column(sa.String(80))
    serial_number: Mapped[str | None] = mapped_column(sa.String(80))
    position: Mapped[str | None] = mapped_column(sa.String(30))
    quantity: Mapped[int] = mapped_column(sa.SmallInteger, default=1, server_default="1")
    installed_date: Mapped[date]
    installed_mileage: Mapped[int | None]
    price: Mapped[Decimal | None]
    labor_cost: Mapped[Decimal | None]
    warranty_expiration_date: Mapped[date | None]
    expected_lifetime_km: Mapped[int | None]
    expected_lifetime_months: Mapped[int | None] = mapped_column(sa.SmallInteger)
    removed_date: Mapped[date | None]
    removed_mileage: Mapped[int | None]
    notes: Mapped[str | None] = mapped_column(sa.Text)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.ForeignKey("users.id", ondelete="SET NULL")
    )

    vehicle: Mapped[Vehicle] = relationship(lazy="raise")
    part_type: Mapped[PartType] = relationship(lazy="raise")
    garage: Mapped[Garage | None] = relationship(lazy="raise")
    maintenance_record: Mapped[MaintenanceRecord | None] = relationship(lazy="raise")

    __table_args__ = (
        sa.CheckConstraint("quantity > 0", name="quantity_positive"),
        sa.CheckConstraint("installed_mileage >= 0", name="installed_mileage_positive"),
        sa.CheckConstraint("removed_mileage >= 0", name="removed_mileage_positive"),
        sa.CheckConstraint("price >= 0", name="price_positive"),
        sa.CheckConstraint("labor_cost >= 0", name="labor_cost_positive"),
        sa.CheckConstraint("expected_lifetime_km > 0", name="expected_lifetime_km_positive"),
        sa.CheckConstraint(
            "expected_lifetime_months > 0", name="expected_lifetime_months_positive"
        ),
        sa.CheckConstraint(
            "removed_date IS NULL OR removed_date >= installed_date", name="removed_after_installed"
        ),
        sa.Index(None, "vehicle_id", "installed_date"),
        sa.Index(
            "ix_part_replacements_installed",
            "vehicle_id",
            "part_type_id",
            postgresql_where=sa.text("removed_date IS NULL"),
        ),
    )

    @property
    def is_installed(self) -> bool:
        return self.removed_date is None

    @property
    def total_cost(self) -> Decimal | None:
        if self.price is None and self.labor_cost is None:
            return None
        return (self.price or Decimal(0)) + (self.labor_cost or Decimal(0))
