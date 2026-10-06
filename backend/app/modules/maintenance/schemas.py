"""Maintenance DTOs."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import Field, StringConstraints

from app.core.schemas import LongText, Mileage, Money, RequestModel, ResponseModel, ShortText
from app.db.catalog import CatalogResponseModel
from app.modules.garages.schemas import GarageSummary
from app.modules.maintenance.models import MaintenanceCategory, MaintenanceKind

TypeName = Annotated[str, StringConstraints(min_length=1, max_length=100)]
IntervalKm = Annotated[int, Field(gt=0, le=1_000_000, examples=[10_000])]
IntervalMonths = Annotated[int, Field(gt=0, le=240, examples=[12])]


# --- Maintenance types ----------------------------------------------------------------------


class MaintenanceTypeCreate(RequestModel):
    name: TypeName
    category: MaintenanceCategory = MaintenanceCategory.OTHER
    description: LongText | None = None
    default_interval_km: IntervalKm | None = None
    default_interval_months: IntervalMonths | None = None


class MaintenanceTypeUpdate(RequestModel):
    name: TypeName | None = None
    category: MaintenanceCategory | None = None
    description: LongText | None = None
    default_interval_km: IntervalKm | None = None
    default_interval_months: IntervalMonths | None = None


class MaintenanceTypeResponse(CatalogResponseModel):
    id: uuid.UUID
    code: str | None = Field(description="Stable identifier of system types (null for custom).")
    name: str = Field(description="Localized in the caller's language for system types.")
    category: MaintenanceCategory
    description: str | None
    default_interval_km: int | None
    default_interval_months: int | None
    is_system: bool
    created_at: datetime
    updated_at: datetime


class MaintenanceTypeSummary(CatalogResponseModel):
    id: uuid.UUID
    code: str | None
    name: str
    category: MaintenanceCategory


# --- Maintenance records --------------------------------------------------------------------


class MaintenanceRecordFields(RequestModel):
    kind: MaintenanceKind | None = None
    title: ShortText | None = Field(
        default=None, description="Defaults to the maintenance type name."
    )
    description: LongText | None = None
    mileage: Mileage | None = Field(default=None, description="Odometer at service time (km).")
    cost: Money | None = Field(
        default=None, description="Total cost; defaults to labor_cost + parts_cost."
    )
    labor_cost: Money | None = None
    parts_cost: Money | None = None
    garage_id: uuid.UUID | None = None
    notes: LongText | None = None


class MaintenanceRecordCreate(MaintenanceRecordFields):
    maintenance_type_id: uuid.UUID
    kind: MaintenanceKind = MaintenanceKind.MAINTENANCE
    service_date: date


class MaintenanceRecordUpdate(MaintenanceRecordFields):
    maintenance_type_id: uuid.UUID | None = None
    service_date: date | None = None


class MaintenanceRecordResponse(ResponseModel):
    id: uuid.UUID
    vehicle_id: uuid.UUID
    maintenance_type: MaintenanceTypeSummary
    kind: MaintenanceKind
    title: str
    description: str | None
    service_date: date
    mileage: int | None
    cost: Decimal | None
    labor_cost: Decimal | None
    parts_cost: Decimal | None
    garage: GarageSummary | None
    notes: str | None
    created_by_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
