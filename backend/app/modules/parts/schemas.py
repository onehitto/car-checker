"""Part DTOs."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Self

from pydantic import Field, StringConstraints, model_validator

from app.core.schemas import LongText, Mileage, Money, RequestModel, ResponseModel
from app.db.catalog import CatalogResponseModel
from app.modules.garages.schemas import GarageSummary
from app.modules.maintenance.calculator import DueStatus
from app.modules.maintenance.schemas import IntervalKm, IntervalMonths
from app.modules.parts.models import PartCategory

PartText = Annotated[str, StringConstraints(min_length=1, max_length=80)]


# --- Part types -----------------------------------------------------------------------------


class PartTypeCreate(RequestModel):
    name: Annotated[str, StringConstraints(min_length=1, max_length=100)]
    category: PartCategory = PartCategory.OTHER
    description: LongText | None = None
    default_lifetime_km: IntervalKm | None = None
    default_lifetime_months: IntervalMonths | None = None


class PartTypeUpdate(RequestModel):
    name: Annotated[str, StringConstraints(min_length=1, max_length=100)] | None = None
    category: PartCategory | None = None
    description: LongText | None = None
    default_lifetime_km: IntervalKm | None = None
    default_lifetime_months: IntervalMonths | None = None


class PartTypeResponse(CatalogResponseModel):
    id: uuid.UUID
    code: str | None
    name: str
    category: PartCategory
    description: str | None
    default_lifetime_km: int | None
    default_lifetime_months: int | None
    is_system: bool
    created_at: datetime
    updated_at: datetime


class PartTypeSummary(CatalogResponseModel):
    id: uuid.UUID
    code: str | None
    name: str
    category: PartCategory


# --- Part replacements ----------------------------------------------------------------------


class PartFields(RequestModel):
    part_name: Annotated[str, StringConstraints(min_length=1, max_length=150)] | None = Field(
        default=None, description="Defaults to the part type name."
    )
    brand: PartText | None = None
    reference_number: PartText | None = None
    serial_number: PartText | None = None
    position: Annotated[str, StringConstraints(min_length=1, max_length=30)] | None = Field(
        default=None, examples=["front", "rear_left"]
    )
    quantity: int | None = Field(default=None, ge=1, le=100)
    installed_mileage: Mileage | None = None
    price: Money | None = None
    labor_cost: Money | None = None
    garage_id: uuid.UUID | None = None
    maintenance_record_id: uuid.UUID | None = Field(
        default=None, description="Maintenance during which the part was installed."
    )
    warranty_expiration_date: date | None = None
    expected_lifetime_km: IntervalKm | None = Field(
        default=None, description="Defaults to the part type lifetime."
    )
    expected_lifetime_months: IntervalMonths | None = Field(
        default=None, description="Defaults to the part type lifetime."
    )
    notes: LongText | None = None


class PartCreate(PartFields):
    part_type_id: uuid.UUID
    installed_date: date
    quantity: int = Field(default=1, ge=1, le=100)

    @model_validator(mode="after")
    def _warranty_after_install(self) -> Self:
        if self.warranty_expiration_date and self.warranty_expiration_date < self.installed_date:
            raise ValueError("warranty_expiration_date cannot be before installed_date.")
        return self


class PartUpdate(PartFields):
    part_type_id: uuid.UUID | None = None
    installed_date: date | None = None
    removed_date: date | None = None
    removed_mileage: Mileage | None = None


class PartLifetime(ResponseModel):
    next_replacement_date: date | None
    next_replacement_mileage: int | None
    remaining_km: int | None
    remaining_days: int | None
    status: DueStatus


class PartResponse(ResponseModel):
    id: uuid.UUID
    vehicle_id: uuid.UUID
    part_type: PartTypeSummary
    part_name: str
    brand: str | None
    reference_number: str | None
    serial_number: str | None
    position: str | None
    quantity: int
    installed_date: date
    installed_mileage: int | None
    price: Decimal | None
    labor_cost: Decimal | None
    total_cost: Decimal | None
    garage: GarageSummary | None
    maintenance_record_id: uuid.UUID | None
    warranty_expiration_date: date | None
    expected_lifetime_km: int | None
    expected_lifetime_months: int | None
    removed_date: date | None
    removed_mileage: int | None
    is_installed: bool
    lifetime: PartLifetime | None = Field(
        default=None, description="Wear status of installed parts with an expected lifetime."
    )
    notes: str | None
    created_by_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
