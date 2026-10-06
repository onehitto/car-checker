"""Maintenance record use cases."""

import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import ColumnElement, Select, delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.clock import Clock
from app.core.exceptions import NotFoundError
from app.core.pagination import Page, PageParams, apply_sort, like_pattern, paginate
from app.core.schemas import ensure_not_future
from app.core.updates import apply_updates
from app.modules.alerts.engine import AlertEngine
from app.modules.expenses.service import ExpenseLedger
from app.modules.garages.service import ensure_garage_usable
from app.modules.maintenance.catalog import CatalogService
from app.modules.maintenance.models import MaintenanceKind, MaintenanceRecord, MaintenanceType
from app.modules.maintenance.schedules import ScheduleService
from app.modules.maintenance.schemas import MaintenanceRecordCreate, MaintenanceRecordUpdate
from app.modules.mileage.models import MileageSource
from app.modules.mileage.service import MileageService
from app.modules.vehicles.access import VehicleContext

RECORD_SORT_FIELDS = {
    "service_date": MaintenanceRecord.service_date,
    "mileage": MaintenanceRecord.mileage,
    "cost": MaintenanceRecord.cost,
    "created_at": MaintenanceRecord.created_at,
}
REQUIRED_FIELDS = frozenset({"maintenance_type_id", "kind", "title", "service_date"})


@dataclass(frozen=True, slots=True)
class MaintenanceFilters:
    maintenance_type_id: uuid.UUID | None = None
    kind: MaintenanceKind | None = None
    garage_id: uuid.UUID | None = None
    date_from: date | None = None
    date_to: date | None = None
    mileage_min: int | None = None
    mileage_max: int | None = None
    cost_min: Decimal | None = None
    cost_max: Decimal | None = None
    q: str | None = None
    sort: str | None = None


@dataclass(frozen=True, slots=True)
class PreviousRecord:
    """Values of a record before it was edited or deleted."""

    type_id: uuid.UUID
    service_date: date
    mileage: int | None


def with_relations(stmt: Select[MaintenanceRecord]) -> Select[MaintenanceRecord]:
    return stmt.options(
        joinedload(MaintenanceRecord.maintenance_type), joinedload(MaintenanceRecord.garage)
    )


def default_total(
    cost: Decimal | None, labor: Decimal | None, parts: Decimal | None
) -> Decimal | None:
    """Total cost, defaulting to labor + parts when only the breakdown is known."""
    if cost is not None or (labor is None and parts is None):
        return cost
    return (labor or Decimal(0)) + (parts or Decimal(0))


class MaintenanceRecordService:
    def __init__(self, session: AsyncSession, clock: Clock) -> None:
        self.session = session
        self.clock = clock
        self.types = CatalogService(session, MaintenanceType, "Maintenance type")
        self.mileage = MileageService(session, clock)
        self.schedules = ScheduleService(session, clock)
        self.ledger = ExpenseLedger(session)
        self.alerts = AlertEngine(session, clock)

    async def list_records(
        self, scope: ColumnElement[bool], filters: MaintenanceFilters, params: PageParams
    ) -> Page[MaintenanceRecord]:
        record = MaintenanceRecord
        stmt = with_relations(select(record).where(scope))
        if filters.maintenance_type_id:
            stmt = stmt.where(record.maintenance_type_id == filters.maintenance_type_id)
        if filters.kind:
            stmt = stmt.where(record.kind == filters.kind)
        if filters.garage_id:
            stmt = stmt.where(record.garage_id == filters.garage_id)
        if filters.date_from:
            stmt = stmt.where(record.service_date >= filters.date_from)
        if filters.date_to:
            stmt = stmt.where(record.service_date <= filters.date_to)
        if filters.mileage_min is not None:
            stmt = stmt.where(record.mileage >= filters.mileage_min)
        if filters.mileage_max is not None:
            stmt = stmt.where(record.mileage <= filters.mileage_max)
        if filters.cost_min is not None:
            stmt = stmt.where(record.cost >= filters.cost_min)
        if filters.cost_max is not None:
            stmt = stmt.where(record.cost <= filters.cost_max)
        if filters.q:
            pattern = like_pattern(filters.q)
            stmt = stmt.where(
                or_(
                    record.title.ilike(pattern, escape="\\"),
                    record.description.ilike(pattern, escape="\\"),
                    record.notes.ilike(pattern, escape="\\"),
                )
            )
        stmt = apply_sort(stmt, filters.sort, RECORD_SORT_FIELDS, "-service_date", record.id)
        return await paginate(self.session, stmt, params)

    async def get(self, vehicle_id: uuid.UUID, record_id: uuid.UUID) -> MaintenanceRecord:
        record = (
            await self.session.scalars(
                with_relations(select(MaintenanceRecord))
                .where(
                    MaintenanceRecord.id == record_id, MaintenanceRecord.vehicle_id == vehicle_id
                )
                .execution_options(populate_existing=True)
            )
        ).one_or_none()
        if record is None:
            raise NotFoundError("Maintenance record")
        return record

    async def create(self, ctx: VehicleContext, data: MaintenanceRecordCreate) -> MaintenanceRecord:
        record = await self.add(ctx, data)
        await self.alerts.sync_vehicle(ctx.vehicle_id)
        await self.session.commit()
        return await self.get(ctx.vehicle_id, record.id)

    async def add(self, ctx: VehicleContext, data: MaintenanceRecordCreate) -> MaintenanceRecord:
        """Create a record inside the caller's transaction (also used by oil changes)."""
        maintenance_type = await self.types.resolve_reference(
            ctx.user.id, data.maintenance_type_id, "maintenance_type_id"
        )
        await ensure_garage_usable(self.session, ctx.user.id, data.garage_id)
        ensure_not_future(data.service_date, self.clock.today(ctx.user.timezone), "service_date")

        values = data.model_dump()
        values["title"] = data.title or maintenance_type.localized_name()
        values["cost"] = default_total(data.cost, data.labor_cost, data.parts_cost)
        record = MaintenanceRecord(**values, vehicle_id=ctx.vehicle_id, created_by_id=ctx.user.id)
        self.session.add(record)
        await self._after_write(ctx, record)
        return record

    async def update(
        self, ctx: VehicleContext, record_id: uuid.UUID, data: MaintenanceRecordUpdate
    ) -> MaintenanceRecord:
        record = await self.change(ctx, record_id, data)
        await self.alerts.sync_vehicle(ctx.vehicle_id)
        await self.session.commit()
        return await self.get(ctx.vehicle_id, record.id)

    async def change(
        self, ctx: VehicleContext, record_id: uuid.UUID, data: MaintenanceRecordUpdate
    ) -> MaintenanceRecord:
        """Update a record inside the caller's transaction (also used by oil changes)."""
        record = await self.get(ctx.vehicle_id, record_id)
        previous = PreviousRecord(record.maintenance_type_id, record.service_date, record.mileage)
        changes = data.model_dump(exclude_unset=True)
        if changes.get("maintenance_type_id"):
            await self.types.resolve_reference(
                ctx.user.id, changes["maintenance_type_id"], "maintenance_type_id"
            )
        if changes.get("garage_id"):
            await ensure_garage_usable(self.session, ctx.user.id, changes["garage_id"])
        if changes.get("service_date"):
            ensure_not_future(
                changes["service_date"], self.clock.today(ctx.user.timezone), "service_date"
            )
        apply_updates(record, data, required=REQUIRED_FIELDS)
        record.cost = default_total(record.cost, record.labor_cost, record.parts_cost)
        await self._after_write(ctx, record, previous)
        return record

    async def delete(self, ctx: VehicleContext, record_id: uuid.UUID) -> None:
        record = await self.get(ctx.vehicle_id, record_id)
        previous = PreviousRecord(record.maintenance_type_id, record.service_date, record.mileage)
        await self.session.execute(
            delete(MaintenanceRecord).where(MaintenanceRecord.id == record.id)
        )
        await self.schedules.sync_with_records(
            ctx.vehicle, previous.type_id, replaced=(previous.service_date, previous.mileage)
        )
        await self.alerts.sync_vehicle(ctx.vehicle_id)
        await self.session.commit()

    async def _after_write(
        self,
        ctx: VehicleContext,
        record: MaintenanceRecord,
        previous: PreviousRecord | None = None,
    ) -> None:
        """Side effects of a saved record, in one transaction: odometer, expense, schedules."""
        vehicle = ctx.vehicle
        if record.mileage is not None:
            vehicle = await self.mileage.lock_vehicle(ctx.vehicle_id)
            await self.mileage.record_odometer(
                vehicle, record.mileage, record.service_date, MileageSource.MAINTENANCE, ctx.user.id
            )
        await self.session.flush()
        await self.ledger.sync_maintenance(record)
        if previous is None:
            await self.schedules.sync_with_records(vehicle, record.maintenance_type_id)
            return
        replaced = (previous.service_date, previous.mileage)
        if previous.type_id != record.maintenance_type_id:
            await self.schedules.sync_with_records(vehicle, previous.type_id, replaced=replaced)
            await self.schedules.sync_with_records(vehicle, record.maintenance_type_id)
        else:
            await self.schedules.sync_with_records(
                vehicle, record.maintenance_type_id, replaced=replaced
            )
