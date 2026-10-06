"""Fuel DTOs."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import Field, StringConstraints

from app.core.schemas import LongText, Mileage, Money, RequestModel, ResponseModel, UnitPrice
from app.core.units import ConsumptionUnit, DistanceUnit
from app.modules.fuel.models import PumpFuel

Liters = Annotated[
    Decimal, Field(gt=0, le=1000, max_digits=8, decimal_places=3, examples=["42.300"])
]
Station = Annotated[str, StringConstraints(min_length=1, max_length=120)]


class FuelRecordCreate(RequestModel):
    """Give at least `liters`; the missing price or total is derived from the other."""

    fill_date: date
    mileage: Mileage
    liters: Liters
    price_per_liter: UnitPrice | None = None
    total_price: Money | None = None
    full_tank: bool = True
    missed_previous: bool = Field(
        default=False, description="Fill-ups were skipped before this one (breaks consumption)."
    )
    fuel_type: PumpFuel | None = None
    gas_station: Station | None = None
    notes: LongText | None = None


class FuelRecordUpdate(RequestModel):
    fill_date: date | None = None
    mileage: Mileage | None = None
    liters: Liters | None = None
    price_per_liter: UnitPrice | None = None
    total_price: Money | None = None
    full_tank: bool | None = None
    missed_previous: bool | None = None
    fuel_type: PumpFuel | None = None
    gas_station: Station | None = None
    notes: LongText | None = None


class FuelRecordResponse(ResponseModel):
    id: uuid.UUID
    vehicle_id: uuid.UUID
    fill_date: date
    mileage: int
    liters: Decimal
    price_per_liter: Decimal | None
    total_price: Decimal | None
    full_tank: bool
    missed_previous: bool
    fuel_type: PumpFuel | None
    gas_station: str | None
    notes: str | None
    distance_since_previous: int | None = Field(
        default=None, description="Km since the previous fill-up."
    )
    consumption_l_100km: float | None = Field(
        default=None, description="Set on full tanks that close a measurable segment."
    )
    created_by_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class MonthlyFuelResponse(ResponseModel):
    month: str = Field(examples=["2026-09"])
    liters: Decimal
    cost: Decimal


class FuelStatisticsResponse(ResponseModel):
    currency: str
    distance_unit: DistanceUnit
    consumption_unit: ConsumptionUnit
    fill_up_count: int
    total_liters: Decimal
    total_cost: Decimal
    distance_tracked: float = Field(description="Distance covered by measurable segments.")
    average_consumption: float | None = Field(description="Distance-weighted, in consumption_unit.")
    last_consumption: float | None
    cost_per_distance_unit: float | None = Field(description="Fuel cost per km or per mile.")
    average_price_per_liter: float | None
    monthly: list[MonthlyFuelResponse]
