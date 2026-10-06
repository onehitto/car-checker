"""Maintenance DTOs."""

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import Field, StringConstraints

from app.core.schemas import LongText, RequestModel, ResponseModel
from app.modules.maintenance.models import MaintenanceCategory

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


class MaintenanceTypeResponse(ResponseModel):
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


class MaintenanceTypeSummary(ResponseModel):
    id: uuid.UUID
    code: str | None
    name: str
    category: MaintenanceCategory
