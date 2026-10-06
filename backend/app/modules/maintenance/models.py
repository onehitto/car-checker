"""Maintenance catalog, records and schedules."""

import uuid
from datetime import date
from decimal import Decimal
from enum import StrEnum

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel, StrEnumType, enum_check
from app.db.catalog import CatalogTypeMixin, catalog_table_args
from app.modules.garages.models import Garage
from app.modules.vehicles.models import Vehicle


class MaintenanceCategory(StrEnum):
    ENGINE = "engine"
    FILTERS = "filters"
    FLUIDS = "fluids"
    BRAKES = "brakes"
    ELECTRICAL = "electrical"
    TIRES = "tires"
    SUSPENSION = "suspension"
    TRANSMISSION = "transmission"
    CLIMATE = "climate"
    INSPECTION = "inspection"
    BODY = "body"
    REPAIR = "repair"
    OTHER = "other"


class MaintenanceKind(StrEnum):
    MAINTENANCE = "maintenance"
    REPAIR = "repair"


class MaintenanceType(CatalogTypeMixin, BaseModel):
    __tablename__ = "maintenance_types"
    translation_prefix = "maintenance_type"

    category: Mapped[MaintenanceCategory] = mapped_column(StrEnumType(MaintenanceCategory))
    default_interval_km: Mapped[int | None]
    default_interval_months: Mapped[int | None] = mapped_column(sa.SmallInteger)

    __table_args__ = (
        *catalog_table_args("maintenance_types"),
        enum_check("category", MaintenanceCategory),
        sa.CheckConstraint("default_interval_km > 0", name="default_interval_km_positive"),
        sa.CheckConstraint("default_interval_months > 0", name="default_interval_months_positive"),
    )


class MaintenanceRecord(BaseModel):
    """A service or repair performed on a vehicle."""

    __tablename__ = "maintenance_records"

    vehicle_id: Mapped[uuid.UUID] = mapped_column(sa.ForeignKey("vehicles.id", ondelete="CASCADE"))
    maintenance_type_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("maintenance_types.id", ondelete="RESTRICT"), index=True
    )
    garage_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.ForeignKey("garages.id", ondelete="SET NULL"), index=True
    )
    kind: Mapped[MaintenanceKind] = mapped_column(
        StrEnumType(MaintenanceKind),
        default=MaintenanceKind.MAINTENANCE,
        server_default=MaintenanceKind.MAINTENANCE.value,
    )
    title: Mapped[str] = mapped_column(sa.String(200))
    description: Mapped[str | None] = mapped_column(sa.Text)
    service_date: Mapped[date]
    mileage: Mapped[int | None]
    cost: Mapped[Decimal | None]
    labor_cost: Mapped[Decimal | None]
    parts_cost: Mapped[Decimal | None]
    notes: Mapped[str | None] = mapped_column(sa.Text)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.ForeignKey("users.id", ondelete="SET NULL")
    )

    vehicle: Mapped[Vehicle] = relationship(lazy="raise")
    maintenance_type: Mapped[MaintenanceType] = relationship(lazy="raise")
    garage: Mapped[Garage | None] = relationship(lazy="raise")

    __table_args__ = (
        enum_check("kind", MaintenanceKind),
        sa.CheckConstraint("mileage >= 0", name="mileage_positive"),
        sa.CheckConstraint("cost >= 0", name="cost_positive"),
        sa.CheckConstraint("labor_cost >= 0", name="labor_cost_positive"),
        sa.CheckConstraint("parts_cost >= 0", name="parts_cost_positive"),
        sa.Index(None, "vehicle_id", "service_date"),
    )
