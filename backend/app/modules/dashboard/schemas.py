"""Dashboard DTOs."""

from decimal import Decimal

from pydantic import Field

from app.core.schemas import ResponseModel
from app.modules.alerts.schemas import AlertResponse, AlertSummary
from app.modules.dashboard.health import HealthLevel
from app.modules.documents.schemas import DocumentResponse
from app.modules.expenses.schemas import ExpenseResponse
from app.modules.maintenance.schemas import MaintenanceRecordResponse, ScheduleResponse
from app.modules.parts.schemas import PartResponse
from app.modules.statistics.schemas import MonthTotal
from app.modules.vehicles.schemas import VehicleResponse


class HealthResponse(ResponseModel):
    score: int = Field(ge=0, le=100)
    level: HealthLevel
    overdue_maintenance: int
    due_maintenance: int
    expired_documents: int
    expiring_documents: int
    worn_parts: int


class MaintenanceOverview(ResponseModel):
    overdue: list[ScheduleResponse]
    upcoming: list[ScheduleResponse] = Field(description="Due, due soon and upcoming.")


class DocumentsOverview(ResponseModel):
    expired: list[DocumentResponse]
    expiring: list[DocumentResponse]


class AlertsOverview(ResponseModel):
    summary: AlertSummary
    latest: list[AlertResponse]


class FuelOverview(ResponseModel):
    total_liters: Decimal
    total_cost: Decimal
    average_consumption_l_100km: float | None
    last_consumption_l_100km: float | None
    cost_per_km: float | None


class CostsOverview(ResponseModel):
    currency: str
    total: Decimal
    this_month: Decimal
    this_year: Decimal
    total_maintenance_cost: Decimal = Field(description="Maintenance, repairs and parts.")
    monthly: list[MonthTotal] = Field(description="The last 12 months, oldest first.")


class VehicleDashboard(ResponseModel):
    vehicle: VehicleResponse
    current_mileage: int
    health: HealthResponse
    maintenance: MaintenanceOverview
    documents: DocumentsOverview
    worn_parts: list[PartResponse]
    alerts: AlertsOverview
    recent_maintenance: list[MaintenanceRecordResponse]
    recent_expenses: list[ExpenseResponse]
    fuel: FuelOverview
    costs: CostsOverview


class UpcomingMaintenance(ScheduleResponse):
    vehicle_name: str


class ExpiringDocument(DocumentResponse):
    vehicle_name: str


class VehicleOverview(ResponseModel):
    vehicle: VehicleResponse
    health: HealthResponse
    open_alerts: int
    next_maintenance: ScheduleResponse | None = Field(description="Most urgent schedule.")


class CurrencyCosts(ResponseModel):
    currency: str
    this_month: Decimal
    this_year: Decimal


class DashboardTotals(ResponseModel):
    vehicles: int
    overdue_maintenance: int
    due_maintenance: int
    expired_documents: int
    expiring_documents: int
    open_alerts: int


class GlobalDashboard(ResponseModel):
    totals: DashboardTotals
    vehicles: list[VehicleOverview]
    upcoming_maintenance: list[UpcomingMaintenance]
    expiring_documents: list[ExpiringDocument]
    alerts: AlertsOverview
    costs: list[CurrencyCosts]
