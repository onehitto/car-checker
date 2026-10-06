"""Tire use cases: inventory, mounting/removal events and rotations."""

import uuid
from collections.abc import Sequence
from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock
from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.core.pagination import Page, PageParams, paginate
from app.core.schemas import ensure_not_future
from app.core.updates import apply_updates
from app.modules.mileage.models import MileageSource
from app.modules.mileage.service import MileageService
from app.modules.tires.models import (
    Tire,
    TireEvent,
    TireEventType,
    TirePosition,
    TireSeason,
    TireStatus,
)
from app.modules.tires.schemas import TireCreate, TireEventCreate, TireRotation, TireUpdate
from app.modules.vehicles.access import VehicleContext

REQUIRED_FIELDS = frozenset({"brand", "size", "season"})


class TireService:
    def __init__(self, session: AsyncSession, clock: Clock) -> None:
        self.session = session
        self.clock = clock
        self.mileage = MileageService(session, clock)

    def _today(self, ctx: VehicleContext) -> date:
        return self.clock.today(ctx.user.timezone)

    async def list_tires(
        self, ctx: VehicleContext, status: TireStatus | None, season: TireSeason | None
    ) -> Sequence[Tire]:
        stmt = select(Tire).where(Tire.vehicle_id == ctx.vehicle_id)
        if status:
            stmt = stmt.where(Tire.status == status)
        if season:
            stmt = stmt.where(Tire.season == season)
        stmt = stmt.order_by(Tire.status, Tire.position.nulls_last(), Tire.created_at)
        return (await self.session.scalars(stmt)).all()

    async def get(self, ctx: VehicleContext, tire_id: uuid.UUID) -> Tire:
        tire = await self.session.scalar(
            select(Tire)
            .where(Tire.id == tire_id, Tire.vehicle_id == ctx.vehicle_id)
            .execution_options(populate_existing=True)
        )
        if tire is None:
            raise NotFoundError("Tire")
        return tire

    async def create(self, ctx: VehicleContext, data: TireCreate) -> Tire:
        today = self._today(ctx)
        for field in ("purchase_date", "installed_date"):
            ensure_not_future(getattr(data, field), today, field)
        mounted = data.position is not None
        tire = Tire(
            **data.model_dump(exclude={"installed_date"}),
            installed_date=(data.installed_date or today) if mounted else data.installed_date,
            status=TireStatus.MOUNTED if mounted else TireStatus.STORED,
            vehicle_id=ctx.vehicle_id,
            created_by_id=ctx.user.id,
        )
        if mounted:
            await self._ensure_position_free(ctx.vehicle_id, data.position)
            self._event(
                ctx,
                tire,
                TireEventType.INSTALLED,
                tire.installed_date or today,
                data.installed_mileage,
                to_position=data.position,
            )
        self.session.add(tire)
        await self._advance_odometer(ctx, data.installed_mileage, tire.installed_date)
        await self.session.commit()
        return await self.get(ctx, tire.id)

    async def update(self, ctx: VehicleContext, tire_id: uuid.UUID, data: TireUpdate) -> Tire:
        tire = await self.get(ctx, tire_id)
        ensure_not_future(data.purchase_date, self._today(ctx), "purchase_date")
        apply_updates(tire, data, required=REQUIRED_FIELDS)
        await self.session.commit()
        return await self.get(ctx, tire.id)

    async def delete(self, ctx: VehicleContext, tire_id: uuid.UUID) -> None:
        result = await self.session.execute(
            delete(Tire).where(Tire.id == tire_id, Tire.vehicle_id == ctx.vehicle_id)
        )
        if result.rowcount == 0:  # type: ignore[attr-defined]
            raise NotFoundError("Tire")
        await self.session.commit()

    # --- Events ---------------------------------------------------------------------------------

    async def list_events(
        self, ctx: VehicleContext, tire_id: uuid.UUID, params: PageParams
    ) -> Page[TireEvent]:
        tire = await self.get(ctx, tire_id)
        stmt = (
            select(TireEvent)
            .where(TireEvent.tire_id == tire.id)
            .order_by(TireEvent.event_date.desc(), TireEvent.created_at.desc())
        )
        return await paginate(self.session, stmt, params)

    async def add_event(
        self, ctx: VehicleContext, tire_id: uuid.UUID, data: TireEventCreate
    ) -> TireEvent:
        tire = await self.get(ctx, tire_id)
        ensure_not_future(data.event_date, self._today(ctx), "event_date")
        event_type = TireEventType(data.event_type)
        from_position = tire.position

        if event_type is TireEventType.INSTALLED:
            if tire.status is TireStatus.DISCARDED:
                raise BusinessRuleError("A discarded tire cannot be installed again.")
            if tire.status is TireStatus.MOUNTED:
                raise BusinessRuleError("The tire is already mounted; use a rotation to move it.")
            await self._ensure_position_free(ctx.vehicle_id, data.to_position)
            tire.status, tire.position = TireStatus.MOUNTED, data.to_position
            tire.installed_date, tire.installed_mileage = data.event_date, data.mileage
        elif event_type in (TireEventType.REMOVED, TireEventType.DISCARDED):
            if tire.status is TireStatus.DISCARDED:
                raise BusinessRuleError("The tire is already discarded.")
            tire.position = None
            tire.status = (
                TireStatus.STORED if event_type is TireEventType.REMOVED else TireStatus.DISCARDED
            )
        if data.tread_depth_mm is not None:
            tire.tread_depth_mm = data.tread_depth_mm
        if data.condition is not None:
            tire.condition = data.condition

        event = self._event(
            ctx,
            tire,
            event_type,
            data.event_date,
            data.mileage,
            from_position=from_position,
            to_position=tire.position if event_type is TireEventType.INSTALLED else None,
            tread_depth_mm=data.tread_depth_mm,
            notes=data.notes,
        )
        await self._advance_odometer(ctx, data.mileage, data.event_date)
        await self.session.commit()
        return event

    async def rotate(self, ctx: VehicleContext, data: TireRotation) -> Sequence[Tire]:
        """Move several mounted tires at once; the final layout must have unique positions."""
        ensure_not_future(data.rotation_date, self._today(ctx), "rotation_date")
        tires = {
            tire.id: tire
            for tire in await self.session.scalars(
                select(Tire).where(
                    Tire.vehicle_id == ctx.vehicle_id,
                    Tire.id.in_([move.tire_id for move in data.moves]),
                )
            )
        }
        for move in data.moves:
            tire = tires.get(move.tire_id)
            if tire is None:
                raise NotFoundError("Tire")
            if tire.status is not TireStatus.MOUNTED:
                raise BusinessRuleError("Only mounted tires can be rotated.")

        moved = {move.tire_id for move in data.moves}
        staying = await self.session.scalars(
            select(Tire.position).where(
                Tire.vehicle_id == ctx.vehicle_id,
                Tire.status == TireStatus.MOUNTED,
                Tire.id.not_in(moved),
            )
        )
        occupied = set(staying)
        clashes = {move.to_position for move in data.moves} & occupied
        if clashes:
            raise BusinessRuleError(
                "Positions already taken by tires that are not moved: "
                + ", ".join(sorted(position.value for position in clashes)),
                fields={"moves": "Duplicate mounted positions after rotation."},
            )

        # Free the positions first (partial unique index), then mount at the new ones.
        for tire in tires.values():
            tire.status = TireStatus.STORED
        await self.session.flush()
        for move in data.moves:
            tire = tires[move.tire_id]
            self._event(
                ctx,
                tire,
                TireEventType.ROTATED,
                data.rotation_date,
                data.mileage,
                from_position=tire.position,
                to_position=move.to_position,
                notes=data.notes,
            )
            tire.status, tire.position = TireStatus.MOUNTED, move.to_position
        await self._advance_odometer(ctx, data.mileage, data.rotation_date)
        await self.session.commit()
        return await self.list_tires(ctx, TireStatus.MOUNTED, None)

    # --- Helpers --------------------------------------------------------------------------------

    def _event(
        self,
        ctx: VehicleContext,
        tire: Tire,
        event_type: TireEventType,
        event_date: date,
        mileage: int | None,
        **values: object,
    ) -> TireEvent:
        event = TireEvent(
            tire_id=tire.id,
            vehicle_id=ctx.vehicle_id,
            event_type=event_type,
            event_date=event_date,
            mileage=mileage,
            created_by_id=ctx.user.id,
            **values,
        )
        self.session.add(event)
        return event

    async def _ensure_position_free(
        self, vehicle_id: uuid.UUID, position: TirePosition | None
    ) -> None:
        taken = await self.session.scalar(
            select(Tire.id).where(
                Tire.vehicle_id == vehicle_id,
                Tire.status == TireStatus.MOUNTED,
                Tire.position == position,
            )
        )
        if taken:
            raise ConflictError(
                f"Another tire is mounted at {position}.", code="TIRE_POSITION_TAKEN"
            )

    async def _advance_odometer(
        self, ctx: VehicleContext, mileage: int | None, on_date: date | None
    ) -> None:
        if mileage is None or on_date is None:
            return
        vehicle = await self.mileage.lock_vehicle(ctx.vehicle_id)
        await self.mileage.record_odometer(
            vehicle, mileage, on_date, MileageSource.TIRE, ctx.user.id
        )
        await self.mileage.alerts.sync_vehicle(ctx.vehicle_id)
