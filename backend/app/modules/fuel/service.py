"""Fuel record use cases and statistics."""

import uuid
from dataclasses import dataclass
from datetime import date

from sqlalchemy import and_, delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock
from app.core.exceptions import NotFoundError, ValidationAppError
from app.core.pagination import Page, PageParams, paginate
from app.core.schemas import ensure_not_future
from app.core.units import (
    KM_PER_MILE,
    ConsumptionUnit,
    DistanceUnit,
    convert_consumption,
    convert_distance,
)
from app.core.updates import apply_updates
from app.modules.alerts.engine import AlertEngine
from app.modules.expenses.service import ExpenseLedger
from app.modules.fuel.calculator import FillUp, FillUpMetrics, analyze, resolve_prices, summarize
from app.modules.fuel.models import FuelRecord, PumpFuel
from app.modules.fuel.schemas import (
    FuelRecordCreate,
    FuelRecordResponse,
    FuelRecordUpdate,
    FuelStatisticsResponse,
)
from app.modules.mileage.models import MileageSource
from app.modules.mileage.service import MileageService
from app.modules.vehicles.access import VehicleContext

REQUIRED_FIELDS = frozenset({"fill_date", "mileage", "liters", "full_tank", "missed_previous"})


@dataclass(frozen=True, slots=True)
class FuelFilters:
    date_from: date | None = None
    date_to: date | None = None
    fuel_type: PumpFuel | None = None


def to_fill_up(record: FuelRecord) -> FillUp:
    return FillUp(
        id=record.id,
        fill_date=record.fill_date,
        mileage=record.mileage,
        liters=record.liters,
        total_price=record.total_price,
        full_tank=record.full_tank,
        missed_previous=record.missed_previous,
    )


def to_response(record: FuelRecord, metrics: FillUpMetrics | None) -> FuelRecordResponse:
    response = FuelRecordResponse.model_validate(record)
    if metrics is None:
        return response
    return response.model_copy(
        update={
            "distance_since_previous": metrics.distance_since_previous,
            "consumption_l_100km": (
                round(metrics.consumption_l_100km, 2)
                if metrics.consumption_l_100km is not None
                else None
            ),
        }
    )


def _round(value: float | None, digits: int = 2) -> float | None:
    return round(value, digits) if value is not None else None


class FuelService:
    def __init__(self, session: AsyncSession, clock: Clock) -> None:
        self.session = session
        self.clock = clock
        self.mileage = MileageService(session, clock)
        self.ledger = ExpenseLedger(session)
        self.alerts = AlertEngine(session, clock)

    async def _records(
        self, vehicle_id: uuid.UUID, date_from: date | None = None, date_to: date | None = None
    ) -> list[FuelRecord]:
        stmt = select(FuelRecord).where(FuelRecord.vehicle_id == vehicle_id)
        if date_from:
            stmt = stmt.where(FuelRecord.fill_date >= date_from)
        if date_to:
            stmt = stmt.where(FuelRecord.fill_date <= date_to)
        return list((await self.session.scalars(stmt)).all())

    async def metrics(self, vehicle_id: uuid.UUID) -> dict[uuid.UUID, FillUpMetrics]:
        metrics, _ = analyze(to_fill_up(record) for record in await self._records(vehicle_id))
        return metrics

    async def list_records(
        self, ctx: VehicleContext, filters: FuelFilters, params: PageParams
    ) -> Page[FuelRecordResponse]:
        stmt = select(FuelRecord).where(FuelRecord.vehicle_id == ctx.vehicle_id)
        if filters.date_from:
            stmt = stmt.where(FuelRecord.fill_date >= filters.date_from)
        if filters.date_to:
            stmt = stmt.where(FuelRecord.fill_date <= filters.date_to)
        if filters.fuel_type:
            stmt = stmt.where(FuelRecord.fuel_type == filters.fuel_type)
        stmt = stmt.order_by(
            FuelRecord.fill_date.desc(), FuelRecord.mileage.desc(), FuelRecord.id.desc()
        )
        page = await paginate(self.session, stmt, params)
        metrics = await self.metrics(ctx.vehicle_id)  # computed over the whole history
        return page.map(lambda record: to_response(record, metrics.get(record.id)))

    async def get(self, ctx: VehicleContext, record_id: uuid.UUID) -> FuelRecord:
        record = await self.session.scalar(
            select(FuelRecord)
            .where(FuelRecord.id == record_id, FuelRecord.vehicle_id == ctx.vehicle_id)
            .execution_options(populate_existing=True)
        )
        if record is None:
            raise NotFoundError("Fuel record")
        return record

    async def get_response(self, ctx: VehicleContext, record_id: uuid.UUID) -> FuelRecordResponse:
        record = await self.get(ctx, record_id)
        return to_response(record, (await self.metrics(ctx.vehicle_id)).get(record.id))

    async def create(self, ctx: VehicleContext, data: FuelRecordCreate) -> FuelRecordResponse:
        record = FuelRecord(
            **data.model_dump(), vehicle_id=ctx.vehicle_id, created_by_id=ctx.user.id
        )
        await self._validate(ctx, record)
        self.session.add(record)
        await self._after_write(ctx, record)
        return await self.get_response(ctx, record.id)

    async def update(
        self, ctx: VehicleContext, record_id: uuid.UUID, data: FuelRecordUpdate
    ) -> FuelRecordResponse:
        record = await self.get(ctx, record_id)
        changes = data.model_dump(exclude_unset=True)
        # A new quantity or unit price recomputes a total that was not sent explicitly.
        if ({"liters", "price_per_liter"} & changes.keys()) and "total_price" not in changes:
            record.total_price = None
        apply_updates(record, data, required=REQUIRED_FIELDS)
        await self._validate(ctx, record)
        await self._after_write(ctx, record)
        return await self.get_response(ctx, record.id)

    async def delete(self, ctx: VehicleContext, record_id: uuid.UUID) -> None:
        result = await self.session.execute(
            delete(FuelRecord).where(
                FuelRecord.id == record_id, FuelRecord.vehicle_id == ctx.vehicle_id
            )
        )
        if result.rowcount == 0:  # type: ignore[attr-defined]
            raise NotFoundError("Fuel record")
        await self.alerts.sync_vehicle(ctx.vehicle_id)
        await self.session.commit()

    async def statistics(
        self,
        ctx: VehicleContext,
        date_from: date | None,
        date_to: date | None,
        distance_unit: DistanceUnit,
        consumption_unit: ConsumptionUnit,
    ) -> FuelStatisticsResponse:
        records = await self._records(ctx.vehicle_id, date_from, date_to)
        stats = summarize([to_fill_up(record) for record in records])

        def consumption(value: float | None) -> float | None:
            return _round(convert_consumption(value, consumption_unit)) if value else None

        cost_per_unit = stats.cost_per_km
        if cost_per_unit is not None and distance_unit is DistanceUnit.MI:
            cost_per_unit *= KM_PER_MILE
        return FuelStatisticsResponse(
            currency=ctx.vehicle.currency,
            distance_unit=distance_unit,
            consumption_unit=consumption_unit,
            fill_up_count=stats.fill_up_count,
            total_liters=stats.total_liters,
            total_cost=stats.total_cost,
            distance_tracked=round(convert_distance(stats.distance_tracked, distance_unit), 1),
            average_consumption=consumption(stats.average_consumption_l_100km),
            last_consumption=consumption(stats.last_consumption_l_100km),
            cost_per_distance_unit=_round(cost_per_unit, 4),
            average_price_per_liter=_round(stats.average_price_per_liter, 4),
            monthly=[
                {"month": month.month, "liters": month.liters, "cost": month.cost}
                for month in stats.monthly
            ],
        )

    async def _validate(self, ctx: VehicleContext, record: FuelRecord) -> None:
        ensure_not_future(record.fill_date, self.clock.today(ctx.user.timezone), "fill_date")
        try:
            record.price_per_liter, record.total_price = resolve_prices(
                record.liters, record.price_per_liter, record.total_price
            )
        except ValueError as exc:
            raise ValidationAppError(fields={"total_price": str(exc)}) from None
        conflict = await self.session.scalar(
            select(FuelRecord.id)
            .where(
                FuelRecord.vehicle_id == ctx.vehicle_id,
                FuelRecord.id != record.id,
                or_(
                    and_(
                        FuelRecord.fill_date < record.fill_date, FuelRecord.mileage > record.mileage
                    ),
                    and_(
                        FuelRecord.fill_date > record.fill_date, FuelRecord.mileage < record.mileage
                    ),
                ),
            )
            .limit(1)
        )
        if conflict is not None:
            raise ValidationAppError(
                fields={
                    "mileage": "Inconsistent with another fill-up: mileage must grow over time."
                }
            )

    async def _after_write(self, ctx: VehicleContext, record: FuelRecord) -> None:
        await self.session.flush()
        vehicle = await self.mileage.lock_vehicle(ctx.vehicle_id)
        await self.mileage.record_odometer(
            vehicle, record.mileage, record.fill_date, MileageSource.FUEL, ctx.user.id
        )
        await self.ledger.sync_fuel(record)
        await self.alerts.sync_vehicle(ctx.vehicle_id)
        await self.session.commit()
