"""Cost and usage statistics, computed with SQL aggregations over the expense ledger."""

import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy import ColumnElement, extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dates import months_between
from app.core.exceptions import ValidationAppError
from app.modules.expenses.models import Expense, ExpenseCategory
from app.modules.fuel.calculator import summarize
from app.modules.fuel.models import FuelRecord
from app.modules.fuel.service import to_fill_up
from app.modules.maintenance.models import MaintenanceKind, MaintenanceRecord, MaintenanceType
from app.modules.mileage.models import MileageEntry
from app.modules.statistics.schemas import (
    CategoryTotal,
    CurrencyStatistics,
    ExpensiveRepair,
    FuelSummary,
    GlobalStatistics,
    MaintenanceFrequency,
    MonthTotal,
    Period,
    VehicleStatistics,
    VehicleTotal,
    YearTotal,
)
from app.modules.vehicles.models import Vehicle

CENT = Decimal("0.01")
TOP_REPAIRS = 5


@dataclass(frozen=True, slots=True)
class StatisticsQuery:
    date_from: date | None = None
    date_to: date | None = None
    year: int | None = None
    categories: list[ExpenseCategory] | None = None


def resolve_period(query: StatisticsQuery, today: date, first_activity: date | None) -> Period:
    """Explicit range, else a calendar year, else first activity -> today."""
    if query.year is not None:
        if query.date_from or query.date_to:
            raise ValidationAppError(fields={"year": "Use either year or date_from/date_to."})
        start, end = date(query.year, 1, 1), min(date(query.year, 12, 31), today)
    else:
        start = query.date_from or first_activity or today
        end = query.date_to or today
    if end < start:
        raise ValidationAppError(fields={"date_to": "Must be on or after date_from."})
    return Period(date_from=start, date_to=end, months=months_between(start, end))


def month_label() -> Any:
    return func.to_char(Expense.expense_date, "YYYY-MM")


class StatisticsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _expense_filter(
        self, scope: ColumnElement[bool], period: Period, query: StatisticsQuery
    ) -> list[ColumnElement[bool]]:
        conditions = [
            scope,
            Expense.expense_date >= period.date_from,
            Expense.expense_date <= period.date_to,
        ]
        if query.categories:
            conditions.append(Expense.category.in_(query.categories))
        return conditions

    async def _first_expense(self, scope: ColumnElement[bool]) -> date | None:
        return await self.session.scalar(select(func.min(Expense.expense_date)).where(scope))

    # --- Per vehicle -----------------------------------------------------------------------------

    async def vehicle_statistics(
        self, vehicle: Vehicle, query: StatisticsQuery, today: date
    ) -> VehicleStatistics:
        scope = Expense.vehicle_id == vehicle.id
        first = await self._first_expense(scope) or vehicle.purchase_date
        period = resolve_period(query, today, first)
        conditions = self._expense_filter(scope, period, query)

        by_category = await self._by_category(conditions)
        total = sum((c.total for c in by_category), Decimal(0))
        distance = await self._distance_driven(vehicle.id, period)
        records = MaintenanceRecord
        record_period = (
            records.vehicle_id == vehicle.id,
            records.service_date >= period.date_from,
            records.service_date <= period.date_to,
        )
        counts = dict(
            (
                await self.session.execute(
                    select(records.kind, func.count()).where(*record_period).group_by(records.kind)
                )
            ).all()
        )
        fuel_records = (
            await self.session.scalars(
                select(FuelRecord).where(
                    FuelRecord.vehicle_id == vehicle.id,
                    FuelRecord.fill_date >= period.date_from,
                    FuelRecord.fill_date <= period.date_to,
                )
            )
        ).all()
        fuel = summarize([to_fill_up(record) for record in fuel_records])

        return VehicleStatistics(
            currency=vehicle.currency,
            period=period,
            total=total,
            by_category=by_category,
            by_month=await self._by_month(conditions),
            by_year=await self._by_year(conditions),
            average_monthly_cost=(total / period.months).quantize(CENT, ROUND_HALF_UP),
            distance_driven_km=distance,
            cost_per_km=round(float(total) / distance, 4) if distance else None,
            maintenance_count=counts.get(MaintenanceKind.MAINTENANCE, 0),
            repair_count=counts.get(MaintenanceKind.REPAIR, 0),
            maintenance_frequency=await self._maintenance_frequency(record_period),
            most_expensive_repairs=await self._expensive_repairs(record_period),
            fuel=FuelSummary(
                total_liters=fuel.total_liters,
                total_cost=fuel.total_cost,
                average_consumption_l_100km=(
                    round(fuel.average_consumption_l_100km, 2)
                    if fuel.average_consumption_l_100km
                    else None
                ),
                cost_per_km=round(fuel.cost_per_km, 4) if fuel.cost_per_km else None,
            ),
        )

    async def _by_category(self, conditions: list[ColumnElement[bool]]) -> list[CategoryTotal]:
        rows = (
            await self.session.execute(
                select(Expense.category, func.sum(Expense.amount), func.count())
                .where(*conditions)
                .group_by(Expense.category)
                .order_by(func.sum(Expense.amount).desc())
            )
        ).all()
        total = sum((row[1] for row in rows), Decimal(0))
        return [
            CategoryTotal(
                category=category,
                total=amount,
                count=count,
                share=round(float(amount / total), 4) if total else 0.0,
            )
            for category, amount, count in rows
        ]

    async def _by_month(self, conditions: list[ColumnElement[bool]]) -> list[MonthTotal]:
        label = month_label()
        rows = await self.session.execute(
            select(label, func.sum(Expense.amount))
            .where(*conditions)
            .group_by(label)
            .order_by(label)
        )
        return [MonthTotal(month=month, total=amount) for month, amount in rows]

    async def _by_year(self, conditions: list[ColumnElement[bool]]) -> list[YearTotal]:
        year = extract("year", Expense.expense_date)
        rows = await self.session.execute(
            select(year, func.sum(Expense.amount)).where(*conditions).group_by(year).order_by(year)
        )
        return [YearTotal(year=int(value), total=amount) for value, amount in rows]

    async def _distance_driven(self, vehicle_id: uuid.UUID, period: Period) -> int | None:
        """Odometer at the end of the period minus odometer at its start."""

        async def reading_on_or_before(day: date) -> int | None:
            return await self.session.scalar(
                select(MileageEntry.mileage)
                .where(MileageEntry.vehicle_id == vehicle_id, MileageEntry.recorded_on <= day)
                .order_by(MileageEntry.recorded_on.desc(), MileageEntry.mileage.desc())
                .limit(1)
            )

        start = await reading_on_or_before(period.date_from)
        if start is None:
            start = await self.session.scalar(
                select(func.min(MileageEntry.mileage)).where(
                    MileageEntry.vehicle_id == vehicle_id,
                    MileageEntry.recorded_on >= period.date_from,
                )
            )
        end = await reading_on_or_before(period.date_to)
        if start is None or end is None or end <= start:
            return None
        return end - start

    async def _maintenance_frequency(
        self, record_period: tuple[ColumnElement[bool], ...]
    ) -> list[MaintenanceFrequency]:
        record = MaintenanceRecord
        count = func.count(record.id)
        rows = (
            await self.session.execute(
                select(
                    MaintenanceType,
                    count,
                    func.coalesce(func.sum(record.cost), 0),
                    func.min(record.service_date),
                    func.max(record.service_date),
                    func.min(record.mileage),
                    func.max(record.mileage),
                    func.count(record.mileage),
                )
                .join(record, record.maintenance_type_id == MaintenanceType.id)
                .where(*record_period)
                .group_by(MaintenanceType.id)
                .order_by(count.desc(), MaintenanceType.name)
            )
        ).all()
        result = []
        for type_, total, cost, first, last, low, high, with_mileage in rows:
            result.append(
                MaintenanceFrequency(
                    maintenance_type=type_,  # type: ignore[arg-type]
                    count=total,
                    total_cost=cost,
                    last_service_date=last,
                    average_interval_days=(last - first).days // (total - 1) if total > 1 else None,
                    average_interval_km=(
                        (high - low) // (with_mileage - 1) if with_mileage > 1 else None
                    ),
                )
            )
        return result

    async def _expensive_repairs(
        self, record_period: tuple[ColumnElement[bool], ...]
    ) -> list[ExpensiveRepair]:
        records = await self.session.scalars(
            select(MaintenanceRecord)
            .where(
                *record_period,
                MaintenanceRecord.kind == MaintenanceKind.REPAIR,
                MaintenanceRecord.cost.is_not(None),
            )
            .order_by(MaintenanceRecord.cost.desc())
            .limit(TOP_REPAIRS)
        )
        return [ExpensiveRepair.model_validate(record) for record in records]

    # --- Across vehicles -------------------------------------------------------------------------

    async def global_statistics(
        self, scope: ColumnElement[bool], query: StatisticsQuery, today: date
    ) -> GlobalStatistics:
        period = resolve_period(query, today, await self._first_expense(scope))
        conditions = self._expense_filter(scope, period, query)
        currency = Vehicle.currency
        base = select().select_from(Expense).join(Vehicle, Vehicle.id == Expense.vehicle_id)

        by_category: dict[str, list[tuple[Any, ...]]] = defaultdict(list)
        for row in await self.session.execute(
            base.add_columns(currency, Expense.category, func.sum(Expense.amount), func.count())
            .where(*conditions)
            .group_by(currency, Expense.category)
            .order_by(func.sum(Expense.amount).desc())
        ):
            by_category[row[0]].append(tuple(row[1:]))

        by_month: dict[str, list[MonthTotal]] = defaultdict(list)
        label = month_label()
        for code, month, amount in await self.session.execute(
            base.add_columns(currency, label, func.sum(Expense.amount))
            .where(*conditions)
            .group_by(currency, label)
            .order_by(label)
        ):
            by_month[code].append(MonthTotal(month=month, total=amount))

        by_vehicle: dict[str, list[VehicleTotal]] = defaultdict(list)
        for code, vehicle_id, nickname, brand, model, amount in await self.session.execute(
            base.add_columns(
                currency,
                Vehicle.id,
                Vehicle.nickname,
                Vehicle.brand,
                Vehicle.model,
                func.sum(Expense.amount),
            )
            .where(*conditions)
            .group_by(currency, Vehicle.id)
            .order_by(func.sum(Expense.amount).desc())
        ):
            by_vehicle[code].append(
                VehicleTotal(
                    vehicle_id=vehicle_id, display_name=nickname or f"{brand} {model}", total=amount
                )
            )

        currencies = []
        for code in sorted(by_category):
            rows = by_category[code]
            total = sum((row[1] for row in rows), Decimal(0))
            currencies.append(
                CurrencyStatistics(
                    currency=code,
                    total=total,
                    by_category=[
                        CategoryTotal(
                            category=category,
                            total=amount,
                            count=count,
                            share=round(float(amount / total), 4) if total else 0.0,
                        )
                        for category, amount, count in rows
                    ],
                    by_month=by_month[code],
                    by_vehicle=by_vehicle[code],
                )
            )
        return GlobalStatistics(period=period, currencies=currencies)
