"""Statistics DTOs. Amounts are in `currency` (the vehicle's currency)."""

import uuid
from datetime import date
from decimal import Decimal

from pydantic import Field

from app.core.schemas import ResponseModel
from app.modules.expenses.models import ExpenseCategory
from app.modules.maintenance.schemas import MaintenanceTypeSummary


class Period(ResponseModel):
    date_from: date
    date_to: date
    months: int


class CategoryTotal(ResponseModel):
    category: ExpenseCategory
    total: Decimal
    count: int
    share: float = Field(description="Share of the period total (0-1).")


class MonthTotal(ResponseModel):
    month: str = Field(examples=["2026-09"])
    total: Decimal


class YearTotal(ResponseModel):
    year: int
    total: Decimal


class MaintenanceFrequency(ResponseModel):
    maintenance_type: MaintenanceTypeSummary
    count: int
    total_cost: Decimal
    last_service_date: date
    average_interval_days: int | None
    average_interval_km: int | None


class ExpensiveRepair(ResponseModel):
    id: uuid.UUID
    title: str
    service_date: date
    mileage: int | None
    cost: Decimal


class FuelSummary(ResponseModel):
    total_liters: Decimal
    total_cost: Decimal
    average_consumption_l_100km: float | None
    cost_per_km: float | None


class VehicleStatistics(ResponseModel):
    currency: str
    period: Period
    total: Decimal
    by_category: list[CategoryTotal]
    by_month: list[MonthTotal]
    by_year: list[YearTotal]
    average_monthly_cost: Decimal
    distance_driven_km: int | None = Field(description="From odometer readings of the period.")
    cost_per_km: float | None
    maintenance_count: int
    repair_count: int
    maintenance_frequency: list[MaintenanceFrequency]
    most_expensive_repairs: list[ExpensiveRepair]
    fuel: FuelSummary


class VehicleTotal(ResponseModel):
    vehicle_id: uuid.UUID
    display_name: str
    total: Decimal


class CurrencyStatistics(ResponseModel):
    currency: str
    total: Decimal
    by_category: list[CategoryTotal]
    by_month: list[MonthTotal]
    by_vehicle: list[VehicleTotal]


class GlobalStatistics(ResponseModel):
    period: Period
    currencies: list[CurrencyStatistics] = Field(
        description="Amounts of different currencies are never added together."
    )
