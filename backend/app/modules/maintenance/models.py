"""Maintenance catalog, records and schedules."""

from enum import StrEnum

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import BaseModel, StrEnumType, enum_check
from app.db.catalog import CatalogTypeMixin, catalog_table_args


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
