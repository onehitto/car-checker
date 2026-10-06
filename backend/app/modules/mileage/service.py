"""Odometer readings and the vehicle's current mileage.

Rules:
* readings are monotonic in time: a reading must be >= every reading on or before its date
  and <= every reading after its date (override with `force`, audited);
* `vehicles.current_mileage` is the mileage of the most recent reading.
"""

import uuid
from dataclasses import dataclass
from datetime import date

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock
from app.core.exceptions import AppError, NotFoundError, ValidationAppError
from app.core.pagination import Page, PageParams, paginate
from app.core.schemas import ensure_not_future
from app.modules.audit.service import RequestMeta, record_audit
from app.modules.mileage.models import MileageEntry, MileageSource
from app.modules.mileage.schemas import MileageCreate
from app.modules.vehicles.access import VehicleContext
from app.modules.vehicles.models import Vehicle


class MileageDecreaseError(AppError):
    status_code = 422
    code = "MILEAGE_DECREASE"
    default_message = "The mileage is lower than a previous reading."


@dataclass(frozen=True, slots=True)
class MileageFilters:
    date_from: date | None = None
    date_to: date | None = None
    source: MileageSource | None = None


class MileageService:
    def __init__(self, session: AsyncSession, clock: Clock) -> None:
        self.session = session
        self.clock = clock

    async def list_entries(
        self, vehicle_id: uuid.UUID, filters: MileageFilters, params: PageParams
    ) -> Page[MileageEntry]:
        stmt = select(MileageEntry).where(MileageEntry.vehicle_id == vehicle_id)
        if filters.date_from:
            stmt = stmt.where(MileageEntry.recorded_on >= filters.date_from)
        if filters.date_to:
            stmt = stmt.where(MileageEntry.recorded_on <= filters.date_to)
        if filters.source:
            stmt = stmt.where(MileageEntry.source == filters.source)
        stmt = stmt.order_by(
            MileageEntry.recorded_on.desc(), MileageEntry.mileage.desc(), MileageEntry.id.desc()
        )
        return await paginate(self.session, stmt, params)

    async def add_reading(
        self, ctx: VehicleContext, data: MileageCreate, meta: RequestMeta
    ) -> MileageEntry | None:
        vehicle = await self.lock_vehicle(ctx.vehicle_id)
        today = self.clock.today(ctx.user.timezone)
        recorded_on = data.recorded_on or today
        ensure_not_future(recorded_on, today, "recorded_on")

        before, after = await self._neighbours(vehicle.id, recorded_on)
        lower_bound = before if before is not None else vehicle.initial_mileage
        if data.force:
            if data.mileage < lower_bound or (after is not None and data.mileage > after):
                record_audit(
                    self.session,
                    "mileage.forced",
                    user_id=ctx.user.id,
                    meta=meta,
                    entity_type="vehicle",
                    entity_id=vehicle.id,
                    details={"previous": vehicle.current_mileage, "new": data.mileage},
                )
        else:
            self._check_monotonic(data.mileage, recorded_on, lower_bound, after)

        entry = None
        if data.record_history:
            entry = MileageEntry(
                vehicle_id=vehicle.id,
                mileage=data.mileage,
                recorded_on=recorded_on,
                source=MileageSource.MANUAL,
                notes=data.notes,
                created_by_id=ctx.user.id,
            )
            self.session.add(entry)
        if after is None:  # the newest reading defines the current odometer
            vehicle.current_mileage = data.mileage
        await self.session.commit()
        return entry

    async def delete_reading(self, ctx: VehicleContext, entry_id: uuid.UUID) -> int:
        vehicle = await self.lock_vehicle(ctx.vehicle_id)
        result = await self.session.execute(
            delete(MileageEntry).where(
                MileageEntry.id == entry_id, MileageEntry.vehicle_id == vehicle.id
            )
        )
        if result.rowcount == 0:  # type: ignore[attr-defined]
            raise NotFoundError("Mileage entry")
        latest = await self.session.scalar(
            select(MileageEntry.mileage)
            .where(MileageEntry.vehicle_id == vehicle.id)
            .order_by(MileageEntry.recorded_on.desc(), MileageEntry.created_at.desc())
            .limit(1)
        )
        vehicle.current_mileage = latest if latest is not None else vehicle.initial_mileage
        await self.session.commit()
        return vehicle.current_mileage

    async def record_odometer(
        self,
        vehicle: Vehicle,
        mileage: int | None,
        on_date: date,
        source: MileageSource,
        user_id: uuid.UUID | None,
    ) -> bool:
        """Record a reading coming from another record (service, fill-up...), if it advances
        the odometer. Never raises: the source record keeps its own mileage either way.
        Runs inside the caller's transaction (no commit).
        """
        if mileage is None or mileage <= vehicle.current_mileage:
            return False
        latest_date = await self.session.scalar(
            select(func.max(MileageEntry.recorded_on)).where(MileageEntry.vehicle_id == vehicle.id)
        )
        if latest_date is not None and on_date < latest_date:
            return False
        self.session.add(
            MileageEntry(
                vehicle_id=vehicle.id,
                mileage=mileage,
                recorded_on=on_date,
                source=source,
                created_by_id=user_id,
            )
        )
        vehicle.current_mileage = mileage
        return True

    @staticmethod
    def initial_entries(vehicle: Vehicle, on_date: date, user_id: uuid.UUID) -> list[MileageEntry]:
        """History rows describing a newly created vehicle's odometer."""
        entries = [
            MileageEntry(
                vehicle_id=vehicle.id,
                mileage=vehicle.initial_mileage,
                recorded_on=vehicle.purchase_date or on_date,
                source=MileageSource.INITIAL,
                created_by_id=user_id,
            )
        ]
        if vehicle.current_mileage > vehicle.initial_mileage:
            entries.append(
                MileageEntry(
                    vehicle_id=vehicle.id,
                    mileage=vehicle.current_mileage,
                    recorded_on=on_date,
                    source=MileageSource.MANUAL,
                    created_by_id=user_id,
                )
            )
        return entries

    async def lock_vehicle(self, vehicle_id: uuid.UUID) -> Vehicle:
        """Serialize concurrent odometer updates of the same vehicle."""
        vehicle = (
            await self.session.scalars(
                select(Vehicle)
                .where(Vehicle.id == vehicle_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        ).one()
        return vehicle

    async def _neighbours(
        self, vehicle_id: uuid.UUID, on_date: date
    ) -> tuple[int | None, int | None]:
        """Highest reading on or before `on_date` and lowest reading after it."""
        before = await self.session.scalar(
            select(func.max(MileageEntry.mileage)).where(
                MileageEntry.vehicle_id == vehicle_id, MileageEntry.recorded_on <= on_date
            )
        )
        after = await self.session.scalar(
            select(func.min(MileageEntry.mileage)).where(
                MileageEntry.vehicle_id == vehicle_id, MileageEntry.recorded_on > on_date
            )
        )
        return before, after

    @staticmethod
    def _check_monotonic(mileage: int, on_date: date, lower: int, upper: int | None) -> None:
        if mileage < lower:
            raise MileageDecreaseError(
                f"The new reading ({mileage} km) is lower than a previous reading "
                f"({lower} km on or before {on_date.isoformat()}).",
                fields={"mileage": f"Must be greater than or equal to {lower}."},
            )
        if upper is not None and mileage > upper:
            raise ValidationAppError(
                f"The reading ({mileage} km) is higher than a later reading ({upper} km).",
                fields={"mileage": f"Must be lower than or equal to {upper}."},
            )
