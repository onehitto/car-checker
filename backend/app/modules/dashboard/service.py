"""Vehicle and user dashboards: aggregates of existing modules, batched to avoid N+1 queries."""

import uuid
from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import ColumnElement, extract, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.clock import Clock
from app.core.dates import add_months, month_key
from app.modules.alerts.models import OPEN_STATUSES, Alert
from app.modules.alerts.service import AlertService
from app.modules.dashboard.health import Health, health_score
from app.modules.dashboard.schemas import (
    AlertsOverview,
    CostsOverview,
    CurrencyCosts,
    DashboardTotals,
    DocumentsOverview,
    ExpiringDocument,
    FuelOverview,
    GlobalDashboard,
    HealthResponse,
    MaintenanceOverview,
    UpcomingMaintenance,
    VehicleDashboard,
    VehicleOverview,
)
from app.modules.documents.expiration import DocumentStatus
from app.modules.documents.models import VehicleDocument
from app.modules.documents.schemas import DocumentResponse
from app.modules.documents.service import to_response as document_response
from app.modules.expenses.models import Expense, ExpenseCategory
from app.modules.fuel.calculator import summarize
from app.modules.fuel.models import FuelRecord
from app.modules.fuel.service import to_fill_up
from app.modules.maintenance.calculator import DueStatus
from app.modules.maintenance.models import MaintenanceRecord, MaintenanceSchedule
from app.modules.maintenance.records import with_relations
from app.modules.maintenance.schedule_state import evaluate_schedule
from app.modules.maintenance.schedules import ScheduleView
from app.modules.parts.lifetime import evaluate_part
from app.modules.parts.models import PartReplacement
from app.modules.parts.service import to_response as part_response
from app.modules.statistics.schemas import MonthTotal
from app.modules.users.models import User
from app.modules.vehicles.access import VehicleContext
from app.modules.vehicles.models import Vehicle, VehicleRole, VehicleStatus
from app.modules.vehicles.service import VehicleService
from app.modules.vehicles.service import to_response as vehicle_response

RECENT_ITEMS = 5
CENT = Decimal("0.01")
UPCOMING_LIMIT = 10
COST_CATEGORIES = (ExpenseCategory.MAINTENANCE, ExpenseCategory.REPAIRS, ExpenseCategory.PARTS)
UPCOMING_STATUSES = (DueStatus.DUE, DueStatus.DUE_SOON, DueStatus.UPCOMING)


def _health(health: Health) -> HealthResponse:
    return HealthResponse.model_validate(health)


def _urgency(view: ScheduleView) -> tuple[int, int]:
    days = view.state.remaining_days
    return -view.state.status.severity, days if days is not None else 10**6


class DashboardService:
    def __init__(self, session: AsyncSession, clock: Clock) -> None:
        self.session = session
        self.clock = clock
        self.alerts = AlertService(session, clock)

    # --- Shared batched loaders ---------------------------------------------------------------

    async def _schedules(
        self, vehicles: dict[uuid.UUID, Vehicle], today: date
    ) -> dict[uuid.UUID, list[ScheduleView]]:
        result: dict[uuid.UUID, list[ScheduleView]] = defaultdict(list)
        schedules = await self.session.scalars(
            select(MaintenanceSchedule)
            .options(joinedload(MaintenanceSchedule.maintenance_type))
            .where(MaintenanceSchedule.vehicle_id.in_(vehicles), MaintenanceSchedule.enabled)
        )
        for schedule in schedules:
            vehicle = vehicles[schedule.vehicle_id]
            state = evaluate_schedule(schedule, vehicle.current_mileage, today)
            result[schedule.vehicle_id].append(ScheduleView(schedule, state))
        for views in result.values():
            views.sort(key=_urgency)
        return result

    async def _documents(
        self, vehicle_ids: list[uuid.UUID], today: date
    ) -> dict[uuid.UUID, list[DocumentResponse]]:
        result: dict[uuid.UUID, list[DocumentResponse]] = defaultdict(list)
        documents = await self.session.scalars(
            select(VehicleDocument)
            .where(VehicleDocument.vehicle_id.in_(vehicle_ids))
            .order_by(VehicleDocument.expiration_date.asc().nulls_last())
        )
        for document in documents:
            result[document.vehicle_id].append(document_response(document, today))
        return result

    async def _worn_parts(
        self, vehicles: dict[uuid.UUID, Vehicle], today: date
    ) -> dict[uuid.UUID, list[PartReplacement]]:
        result: dict[uuid.UUID, list[PartReplacement]] = defaultdict(list)
        parts = await self.session.scalars(
            select(PartReplacement)
            .options(joinedload(PartReplacement.part_type), joinedload(PartReplacement.garage))
            .where(
                PartReplacement.vehicle_id.in_(vehicles),
                PartReplacement.removed_date.is_(None),
                or_(
                    PartReplacement.expected_lifetime_km.is_not(None),
                    PartReplacement.expected_lifetime_months.is_not(None),
                ),
            )
        )
        for part in parts:
            state = evaluate_part(part, vehicles[part.vehicle_id].current_mileage, today)
            if state is not None and state.status.is_at_least(DueStatus.DUE_SOON):
                result[part.vehicle_id].append(part)
        return result

    async def _alerts_overview(
        self, user_id: uuid.UUID, vehicle_id: uuid.UUID | None
    ) -> AlertsOverview:
        clause: ColumnElement[bool] = Alert.user_id == user_id
        if vehicle_id is not None:
            clause = clause & (Alert.vehicle_id == vehicle_id)
        latest = await self.session.scalars(
            select(Alert)
            .where(clause, Alert.status.in_(OPEN_STATUSES))
            .order_by(Alert.created_at.desc())
            .limit(RECENT_ITEMS)
        )
        return AlertsOverview(
            summary=await self.alerts.summary(user_id, vehicle_id),
            latest=list(latest),
        )

    # --- Vehicle dashboard --------------------------------------------------------------------

    async def vehicle_dashboard(self, ctx: VehicleContext) -> VehicleDashboard:
        vehicle, user = ctx.vehicle, ctx.user
        today = self.clock.today(user.timezone)
        vehicles = {vehicle.id: vehicle}

        schedules = (await self._schedules(vehicles, today))[vehicle.id]
        documents = (await self._documents([vehicle.id], today))[vehicle.id]
        parts = (await self._worn_parts(vehicles, today))[vehicle.id]
        health = health_score(
            (view.state.status for view in schedules),
            (document.status for document in documents),
            (
                state.status
                for part in parts
                if (state := evaluate_part(part, vehicle.current_mileage, today))
            ),
        )

        recent_maintenance = await self.session.scalars(
            with_relations(select(MaintenanceRecord))
            .where(MaintenanceRecord.vehicle_id == vehicle.id)
            .order_by(MaintenanceRecord.service_date.desc(), MaintenanceRecord.id.desc())
            .limit(RECENT_ITEMS)
        )
        recent_expenses = await self.session.scalars(
            select(Expense)
            .where(Expense.vehicle_id == vehicle.id)
            .order_by(Expense.expense_date.desc(), Expense.id.desc())
            .limit(RECENT_ITEMS)
        )
        fuel_records = await self.session.scalars(
            select(FuelRecord).where(FuelRecord.vehicle_id == vehicle.id)
        )
        fuel = summarize([to_fill_up(record) for record in fuel_records])

        return VehicleDashboard(
            vehicle=vehicle_response(vehicle, ctx.role),
            current_mileage=vehicle.current_mileage,
            health=_health(health),
            maintenance=MaintenanceOverview(
                overdue=[v.to_response() for v in schedules if v.state.status is DueStatus.OVERDUE],
                upcoming=[
                    v.to_response() for v in schedules if v.state.status in UPCOMING_STATUSES
                ],
            ),
            documents=DocumentsOverview(
                expired=[d for d in documents if d.status is DocumentStatus.EXPIRED],
                expiring=[d for d in documents if d.status is DocumentStatus.EXPIRING_SOON],
            ),
            worn_parts=[part_response(part, vehicle.current_mileage, today) for part in parts],
            alerts=await self._alerts_overview(user.id, vehicle.id),
            recent_maintenance=list(recent_maintenance),
            recent_expenses=list(recent_expenses),
            fuel=FuelOverview(
                total_liters=fuel.total_liters,
                total_cost=fuel.total_cost,
                average_consumption_l_100km=_round(fuel.average_consumption_l_100km),
                last_consumption_l_100km=_round(fuel.last_consumption_l_100km),
                cost_per_km=_round(fuel.cost_per_km, 4),
            ),
            costs=await self._costs(vehicle, today),
        )

    async def _costs(self, vehicle: Vehicle, today: date) -> CostsOverview:
        amount = func.coalesce(func.sum(Expense.amount), 0)
        scope = Expense.vehicle_id == vehicle.id
        year = extract("year", Expense.expense_date)
        month = extract("month", Expense.expense_date)

        async def total(*conditions: Any) -> Decimal:
            value = await self.session.scalar(select(amount).where(scope, *conditions))
            return Decimal(value or 0).quantize(CENT)

        first_month = add_months(today.replace(day=1), -11)
        label = func.to_char(Expense.expense_date, "YYYY-MM")
        monthly_rows: dict[str, Decimal] = dict(
            (
                await self.session.execute(
                    select(label, amount)
                    .where(scope, Expense.expense_date >= first_month)
                    .group_by(label)
                )
            ).all()
        )
        months = [month_key(add_months(first_month, offset)) for offset in range(12)]
        return CostsOverview(
            currency=vehicle.currency,
            total=await total(),
            this_month=await total(year == today.year, month == today.month),
            this_year=await total(year == today.year),
            total_maintenance_cost=await total(Expense.category.in_(COST_CATEGORIES)),
            monthly=[
                MonthTotal(month=key, total=Decimal(monthly_rows.get(key, 0)).quantize(CENT))
                for key in months
            ],
        )

    # --- User dashboard -----------------------------------------------------------------------

    async def global_dashboard(self, user: User) -> GlobalDashboard:
        today = self.clock.today(user.timezone)
        accessible = await VehicleService(self.session, self.clock).accessible_vehicles(
            user, status=VehicleStatus.ACTIVE
        )
        vehicles = {vehicle.id: vehicle for vehicle, _ in accessible}
        roles: dict[uuid.UUID, VehicleRole] = {vehicle.id: role for vehicle, role in accessible}
        ids = list(vehicles)

        schedules = await self._schedules(vehicles, today) if ids else {}
        documents = await self._documents(ids, today) if ids else {}
        parts = await self._worn_parts(vehicles, today) if ids else {}
        open_alerts = dict(
            (
                await self.session.execute(
                    select(Alert.vehicle_id, func.count())
                    .where(Alert.user_id == user.id, Alert.status.in_(OPEN_STATUSES))
                    .group_by(Alert.vehicle_id)
                )
            ).all()
        )

        overviews: list[VehicleOverview] = []
        upcoming: list[UpcomingMaintenance] = []
        expiring: list[ExpiringDocument] = []
        healths: list[Health] = []
        for vehicle_id, vehicle in vehicles.items():
            views = schedules.get(vehicle_id, [])
            docs = documents.get(vehicle_id, [])
            worn = parts.get(vehicle_id, [])
            health = health_score(
                (view.state.status for view in views),
                (doc.status for doc in docs),
                (
                    state.status
                    for part in worn
                    if (state := evaluate_part(part, vehicle.current_mileage, today))
                ),
            )
            healths.append(health)
            # The most urgent schedule, else the next one in time.
            chosen = next(
                (v for v in views if v.state.status.is_at_least(DueStatus.UPCOMING)),
                views[0] if views else None,
            )
            overviews.append(
                VehicleOverview(
                    vehicle=vehicle_response(vehicle, roles[vehicle_id]),
                    health=_health(health),
                    open_alerts=open_alerts.get(vehicle_id, 0),
                    next_maintenance=chosen.to_response() if chosen else None,
                )
            )
            upcoming.extend(
                UpcomingMaintenance(
                    **view.to_response().model_dump(), vehicle_name=vehicle.display_name
                )
                for view in views
                if view.state.status.is_at_least(DueStatus.UPCOMING)
            )
            expiring.extend(
                ExpiringDocument(**doc.model_dump(), vehicle_name=vehicle.display_name)
                for doc in docs
                if doc.status is not DocumentStatus.VALID
            )

        upcoming.sort(
            key=lambda item: (
                -item.status.severity,
                item.remaining_days if item.remaining_days is not None else 10**6,
            )
        )
        expiring.sort(key=lambda doc: doc.days_until_expiration or 0)
        overviews.sort(key=lambda overview: overview.health.score)

        return GlobalDashboard(
            totals=DashboardTotals(
                vehicles=len(vehicles),
                overdue_maintenance=sum(h.overdue_maintenance for h in healths),
                due_maintenance=sum(h.due_maintenance for h in healths),
                expired_documents=sum(h.expired_documents for h in healths),
                expiring_documents=sum(h.expiring_documents for h in healths),
                open_alerts=sum(open_alerts.values()),
            ),
            vehicles=overviews,
            upcoming_maintenance=upcoming[:UPCOMING_LIMIT],
            expiring_documents=expiring,
            alerts=await self._alerts_overview(user.id, None),
            costs=await self._costs_by_currency(ids, today),
        )

    async def _costs_by_currency(
        self, vehicle_ids: list[uuid.UUID], today: date
    ) -> list[CurrencyCosts]:
        if not vehicle_ids:
            return []
        year = extract("year", Expense.expense_date)
        month = extract("month", Expense.expense_date)
        this_month = func.coalesce(func.sum(Expense.amount).filter(month == today.month), 0)
        rows = await self.session.execute(
            select(Vehicle.currency, this_month, func.coalesce(func.sum(Expense.amount), 0))
            .join(Vehicle, Vehicle.id == Expense.vehicle_id)
            .where(Expense.vehicle_id.in_(vehicle_ids), year == today.year)
            .group_by(Vehicle.currency)
            .order_by(Vehicle.currency)
        )
        return [
            CurrencyCosts(
                currency=currency,
                this_month=Decimal(month_total).quantize(CENT),
                this_year=Decimal(year_total).quantize(CENT),
            )
            for currency, month_total, year_total in rows
        ]


def _round(value: float | None, digits: int = 2) -> float | None:
    return round(value, digits) if value is not None else None
