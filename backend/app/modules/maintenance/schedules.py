"""Maintenance schedule use cases and their synchronisation with maintenance records."""

import uuid
from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.clock import Clock
from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.core.schemas import ensure_not_future
from app.core.updates import apply_updates
from app.modules.maintenance.calculator import (
    DueBaseline,
    DueRule,
    DueState,
    DueStatus,
    next_service,
)
from app.modules.maintenance.catalog import CatalogService
from app.modules.maintenance.models import (
    MaintenanceRecord,
    MaintenanceSchedule,
    MaintenanceType,
)
from app.modules.maintenance.schedule_state import evaluate_schedule
from app.modules.maintenance.schemas import ScheduleCreate, ScheduleResponse, ScheduleUpdate
from app.modules.vehicles.access import VehicleContext
from app.modules.vehicles.models import Vehicle


@dataclass(frozen=True, slots=True)
class ScheduleView:
    schedule: MaintenanceSchedule
    state: DueState

    def to_response(self) -> ScheduleResponse:
        s = self.schedule
        return ScheduleResponse.model_validate(
            {
                "id": s.id,
                "vehicle_id": s.vehicle_id,
                "maintenance_type": s.maintenance_type,
                "interval_km": s.interval_km,
                "interval_months": s.interval_months,
                "last_service_date": s.last_service_date,
                "last_service_mileage": s.last_service_mileage,
                "next_service_date": s.next_service_date,
                "next_service_mileage": s.next_service_mileage,
                "warning_before_km": s.warning_before_km,
                "warning_before_days": s.warning_before_days,
                "enabled": s.enabled,
                "notes": s.notes,
                "remaining_km": self.state.remaining_km,
                "remaining_days": self.state.remaining_days,
                "overdue_km": self.state.overdue_km,
                "overdue_days": self.state.overdue_days,
                "status": self.state.status,
                "due_reason": self.state.due_reason,
                "created_at": s.created_at,
                "updated_at": s.updated_at,
            }
        )


def recompute_next(
    schedule: MaintenanceSchedule,
    vehicle: Vehicle,
    explicit_next_date: date | None = None,
    explicit_next_mileage: int | None = None,
) -> None:
    """Persist next_service_* from the last service, explicit values or the vehicle baseline."""
    rule = DueRule(
        interval_km=schedule.interval_km,
        interval_months=schedule.interval_months,
        warning_km=schedule.warning_before_km,
        warning_days=schedule.warning_before_days,
    )
    baseline = DueBaseline(
        last_date=schedule.last_service_date,
        last_mileage=schedule.last_service_mileage,
        explicit_next_date=explicit_next_date,
        explicit_next_mileage=explicit_next_mileage,
        fallback_date=vehicle.purchase_date or vehicle.created_at.date(),
        fallback_mileage=vehicle.initial_mileage,
    )
    schedule.next_service_date, schedule.next_service_mileage = next_service(rule, baseline)


def _max(a: Any, b: Any) -> Any:
    if a is None:
        return b
    if b is None:
        return a
    return max(a, b)


class ScheduleService:
    def __init__(self, session: AsyncSession, clock: Clock) -> None:
        self.session = session
        self.clock = clock
        self.types = CatalogService(session, MaintenanceType, "Maintenance type")

    # --- Queries ---------------------------------------------------------------------------------

    async def list_views(
        self, ctx: VehicleContext, statuses: set[DueStatus] | None = None
    ) -> list[ScheduleView]:
        """Schedules of the vehicle, most urgent first."""
        schedules = (
            await self.session.scalars(
                select(MaintenanceSchedule)
                .options(joinedload(MaintenanceSchedule.maintenance_type))
                .where(MaintenanceSchedule.vehicle_id == ctx.vehicle_id)
            )
        ).all()
        today = self.clock.today(ctx.user.timezone)
        views = [
            ScheduleView(s, evaluate_schedule(s, ctx.vehicle.current_mileage, today))
            for s in schedules
        ]
        if statuses:
            views = [v for v in views if v.state.status in statuses]
        return sorted(
            views,
            key=lambda v: (
                -v.state.status.severity,
                v.state.remaining_days if v.state.remaining_days is not None else 10**6,
                v.schedule.maintenance_type.name,
            ),
        )

    async def get_view(self, ctx: VehicleContext, schedule_id: uuid.UUID) -> ScheduleView:
        schedule = await self._get(ctx.vehicle_id, schedule_id)
        today = self.clock.today(ctx.user.timezone)
        return ScheduleView(
            schedule, evaluate_schedule(schedule, ctx.vehicle.current_mileage, today)
        )

    async def _get(self, vehicle_id: uuid.UUID, schedule_id: uuid.UUID) -> MaintenanceSchedule:
        schedule = (
            await self.session.scalars(
                select(MaintenanceSchedule)
                .options(joinedload(MaintenanceSchedule.maintenance_type))
                .where(
                    MaintenanceSchedule.id == schedule_id,
                    MaintenanceSchedule.vehicle_id == vehicle_id,
                )
                .execution_options(populate_existing=True)
            )
        ).one_or_none()
        if schedule is None:
            raise NotFoundError("Maintenance schedule")
        return schedule

    # --- Commands --------------------------------------------------------------------------------

    async def create(self, ctx: VehicleContext, data: ScheduleCreate) -> ScheduleView:
        maintenance_type = await self.types.resolve_reference(
            ctx.user.id, data.maintenance_type_id, "maintenance_type_id"
        )
        existing = await self.session.scalar(
            select(MaintenanceSchedule.id).where(
                MaintenanceSchedule.vehicle_id == ctx.vehicle_id,
                MaintenanceSchedule.maintenance_type_id == maintenance_type.id,
            )
        )
        if existing:
            raise ConflictError(
                "This vehicle already has a schedule for this maintenance type.",
                code="SCHEDULE_EXISTS",
            )
        self._check_dates(ctx, data.last_service_date)

        interval_km = data.interval_km or maintenance_type.default_interval_km
        interval_months = data.interval_months or maintenance_type.default_interval_months
        if interval_km is None and interval_months is None:
            raise ValidationAppError(
                fields={"interval_km": "Set interval_km and/or interval_months."}
            )

        schedule = MaintenanceSchedule(
            **data.model_dump(
                exclude={
                    "interval_km",
                    "interval_months",
                    "next_service_date",
                    "next_service_mileage",
                }
            ),
            interval_km=interval_km,
            interval_months=interval_months,
            vehicle_id=ctx.vehicle_id,
        )
        if schedule.last_service_date is None and schedule.last_service_mileage is None:
            last_date, last_mileage = await self._latest_service(
                ctx.vehicle_id, maintenance_type.id
            )
            schedule.last_service_date, schedule.last_service_mileage = last_date, last_mileage
        recompute_next(schedule, ctx.vehicle, data.next_service_date, data.next_service_mileage)
        self.session.add(schedule)
        await self.session.commit()
        return await self.get_view(ctx, schedule.id)

    async def update(
        self, ctx: VehicleContext, schedule_id: uuid.UUID, data: ScheduleUpdate
    ) -> ScheduleView:
        schedule = await self._get(ctx.vehicle_id, schedule_id)
        changes = data.model_dump(exclude_unset=True)
        self._check_dates(ctx, changes.get("last_service_date"))

        # Explicit next values: taken from the request, else kept unless the intervals change
        # (then they are recomputed from the last service or the vehicle baseline).
        intervals_changed = bool({"interval_km", "interval_months"} & changes.keys())
        explicit: dict[str, Any] = {}
        for field in ("next_service_date", "next_service_mileage"):
            if field in changes:
                explicit[field] = changes[field]
            else:
                explicit[field] = None if intervals_changed else getattr(schedule, field)

        apply_updates(
            schedule, data, required={"warning_before_km", "warning_before_days", "enabled"}
        )
        if schedule.interval_km is None and schedule.interval_months is None:
            raise ValidationAppError(
                fields={"interval_km": "Set interval_km and/or interval_months."}
            )
        explicit_date, explicit_mileage = (
            explicit["next_service_date"],
            explicit["next_service_mileage"],
        )
        recompute_next(schedule, ctx.vehicle, explicit_date, explicit_mileage)
        await self.session.commit()
        return await self.get_view(ctx, schedule.id)

    async def delete(self, ctx: VehicleContext, schedule_id: uuid.UUID) -> None:
        result = await self.session.execute(
            delete(MaintenanceSchedule).where(
                MaintenanceSchedule.id == schedule_id,
                MaintenanceSchedule.vehicle_id == ctx.vehicle_id,
            )
        )
        if result.rowcount == 0:  # type: ignore[attr-defined]
            raise NotFoundError("Maintenance schedule")
        await self.session.commit()

    # --- Synchronisation with maintenance records ------------------------------------------------

    async def sync_with_records(
        self,
        vehicle: Vehicle,
        maintenance_type_id: uuid.UUID,
        *,
        replaced: tuple[date, int | None] | None = None,
    ) -> None:
        """Move the schedule of this type forward after records changed (no commit).

        `replaced` holds the (date, mileage) of a record that was edited or deleted: when the
        schedule's last service came from it, the last service is recomputed from the
        remaining records instead of only moving forward.
        """
        schedule = await self.session.scalar(
            select(MaintenanceSchedule).where(
                MaintenanceSchedule.vehicle_id == vehicle.id,
                MaintenanceSchedule.maintenance_type_id == maintenance_type_id,
            )
        )
        if schedule is None:
            return
        latest_date, latest_mileage = await self._latest_service(vehicle.id, maintenance_type_id)
        replaced_date, replaced_mileage = replaced if replaced else (None, None)
        if replaced_date is not None and schedule.last_service_date == replaced_date:
            schedule.last_service_date = latest_date
        else:
            schedule.last_service_date = _max(schedule.last_service_date, latest_date)
        if replaced_mileage is not None and schedule.last_service_mileage == replaced_mileage:
            schedule.last_service_mileage = latest_mileage
        else:
            schedule.last_service_mileage = _max(schedule.last_service_mileage, latest_mileage)
        recompute_next(schedule, vehicle)

    async def _latest_service(
        self, vehicle_id: uuid.UUID, maintenance_type_id: uuid.UUID
    ) -> tuple[date | None, int | None]:
        await self.session.flush()
        row = (
            await self.session.execute(
                select(
                    func.max(MaintenanceRecord.service_date), func.max(MaintenanceRecord.mileage)
                ).where(
                    MaintenanceRecord.vehicle_id == vehicle_id,
                    MaintenanceRecord.maintenance_type_id == maintenance_type_id,
                )
            )
        ).one()
        return row[0], row[1]

    def _check_dates(self, ctx: VehicleContext, last_service_date: date | None) -> None:
        ensure_not_future(
            last_service_date, self.clock.today(ctx.user.timezone), "last_service_date"
        )
