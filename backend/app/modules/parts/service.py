"""Part replacement use cases and lifetime evaluation."""

import uuid
from dataclasses import dataclass
from datetime import date

from sqlalchemy import ColumnElement, Select, delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.clock import Clock
from app.core.exceptions import NotFoundError, ValidationAppError
from app.core.pagination import Page, PageParams, apply_sort, like_pattern, paginate
from app.core.schemas import ensure_not_future
from app.core.updates import apply_updates
from app.modules.garages.service import ensure_garage_usable
from app.modules.maintenance.calculator import DueBaseline, DueRule, DueState, compute_due
from app.modules.maintenance.catalog import CatalogService
from app.modules.maintenance.models import MaintenanceRecord
from app.modules.mileage.models import MileageSource
from app.modules.mileage.service import MileageService
from app.modules.parts.models import PartReplacement, PartType
from app.modules.parts.schemas import PartCreate, PartLifetime, PartResponse, PartUpdate
from app.modules.vehicles.access import VehicleContext

PART_WARNING_KM = 1000
PART_WARNING_DAYS = 30
PART_SORT_FIELDS = {
    "installed_date": PartReplacement.installed_date,
    "installed_mileage": PartReplacement.installed_mileage,
    "price": PartReplacement.price,
    "created_at": PartReplacement.created_at,
}
REQUIRED_FIELDS = frozenset({"part_type_id", "part_name", "quantity", "installed_date"})


@dataclass(frozen=True, slots=True)
class PartFilters:
    part_type_id: uuid.UUID | None = None
    installed: bool | None = None
    date_from: date | None = None
    date_to: date | None = None
    q: str | None = None
    sort: str | None = None


def evaluate_part(part: PartReplacement, current_mileage: int, today: date) -> DueState | None:
    """Wear status of an installed part with an expected lifetime (None otherwise)."""
    if not part.is_installed or (
        part.expected_lifetime_km is None and part.expected_lifetime_months is None
    ):
        return None
    rule = DueRule(
        interval_km=part.expected_lifetime_km,
        interval_months=part.expected_lifetime_months,
        warning_km=PART_WARNING_KM,
        warning_days=PART_WARNING_DAYS,
    )
    baseline = DueBaseline(last_date=part.installed_date, last_mileage=part.installed_mileage)
    return compute_due(rule, baseline, current_mileage, today)


def to_response(part: PartReplacement, current_mileage: int, today: date) -> PartResponse:
    state = evaluate_part(part, current_mileage, today)
    lifetime = (
        PartLifetime(
            next_replacement_date=state.next_service_date,
            next_replacement_mileage=state.next_service_mileage,
            remaining_km=state.remaining_km,
            remaining_days=state.remaining_days,
            status=state.status,
        )
        if state
        else None
    )
    return PartResponse.model_validate(part).model_copy(update={"lifetime": lifetime})


def with_relations(stmt: Select[tuple[PartReplacement]]) -> Select[tuple[PartReplacement]]:
    return stmt.options(joinedload(PartReplacement.part_type), joinedload(PartReplacement.garage))


class PartService:
    def __init__(self, session: AsyncSession, clock: Clock) -> None:
        self.session = session
        self.clock = clock
        self.types = CatalogService(session, PartType, "Part type")
        self.mileage = MileageService(session, clock)

    def today(self, ctx: VehicleContext) -> date:
        return self.clock.today(ctx.user.timezone)

    async def list_parts(
        self, ctx: VehicleContext, filters: PartFilters, params: PageParams
    ) -> Page[PartResponse]:
        part = PartReplacement
        stmt = with_relations(select(part).where(part.vehicle_id == ctx.vehicle_id))
        if filters.part_type_id:
            stmt = stmt.where(part.part_type_id == filters.part_type_id)
        if filters.installed is True:
            stmt = stmt.where(part.removed_date.is_(None))
        elif filters.installed is False:
            stmt = stmt.where(part.removed_date.is_not(None))
        if filters.date_from:
            stmt = stmt.where(part.installed_date >= filters.date_from)
        if filters.date_to:
            stmt = stmt.where(part.installed_date <= filters.date_to)
        if filters.q:
            pattern = like_pattern(filters.q)
            stmt = stmt.where(
                or_(
                    part.part_name.ilike(pattern, escape="\\"),
                    part.brand.ilike(pattern, escape="\\"),
                    part.reference_number.ilike(pattern, escape="\\"),
                )
            )
        stmt = apply_sort(stmt, filters.sort, PART_SORT_FIELDS, "-installed_date", part.id)
        page = await paginate(self.session, stmt, params)
        today, mileage = self.today(ctx), ctx.vehicle.current_mileage
        return page.map(lambda p: to_response(p, mileage, today))

    async def get(self, ctx: VehicleContext, part_id: uuid.UUID) -> PartReplacement:
        part = (
            await self.session.scalars(
                with_relations(select(PartReplacement))
                .where(PartReplacement.id == part_id, PartReplacement.vehicle_id == ctx.vehicle_id)
                .execution_options(populate_existing=True)
            )
        ).one_or_none()
        if part is None:
            raise NotFoundError("Part")
        return part

    async def create(self, ctx: VehicleContext, data: PartCreate) -> PartReplacement:
        part_type = await self.types.resolve_reference(
            ctx.user.id, data.part_type_id, "part_type_id"
        )
        await self._validate_references(ctx, data.garage_id, data.maintenance_record_id)
        ensure_not_future(data.installed_date, self.today(ctx), "installed_date")

        values = data.model_dump()
        values["part_name"] = data.part_name or part_type.localized_name()
        if "expected_lifetime_km" not in data.model_fields_set:
            values["expected_lifetime_km"] = part_type.default_lifetime_km
        if "expected_lifetime_months" not in data.model_fields_set:
            values["expected_lifetime_months"] = part_type.default_lifetime_months
        part = PartReplacement(**values, vehicle_id=ctx.vehicle_id, created_by_id=ctx.user.id)
        self.session.add(part)
        await self.session.flush()
        await self._retire_previous(part)
        await self._advance_odometer(ctx, part)
        await self.session.commit()
        return await self.get(ctx, part.id)

    async def update(
        self, ctx: VehicleContext, part_id: uuid.UUID, data: PartUpdate
    ) -> PartReplacement:
        part = await self.get(ctx, part_id)
        changes = data.model_dump(exclude_unset=True)
        if changes.get("part_type_id"):
            await self.types.resolve_reference(ctx.user.id, changes["part_type_id"], "part_type_id")
        await self._validate_references(
            ctx, changes.get("garage_id"), changes.get("maintenance_record_id")
        )
        for field in ("installed_date", "removed_date"):
            ensure_not_future(changes.get(field), self.today(ctx), field)
        apply_updates(part, data, required=REQUIRED_FIELDS)
        if part.removed_date is not None and part.removed_date < part.installed_date:
            raise ValidationAppError(fields={"removed_date": "Cannot be before installed_date."})
        if (
            part.warranty_expiration_date is not None
            and part.warranty_expiration_date < part.installed_date
        ):
            raise ValidationAppError(
                fields={"warranty_expiration_date": "Cannot be before installed_date."}
            )
        await self._advance_odometer(ctx, part)
        await self.session.commit()
        return await self.get(ctx, part.id)

    async def delete(self, ctx: VehicleContext, part_id: uuid.UUID) -> None:
        result = await self.session.execute(
            delete(PartReplacement).where(
                PartReplacement.id == part_id, PartReplacement.vehicle_id == ctx.vehicle_id
            )
        )
        if result.rowcount == 0:  # type: ignore[attr-defined]
            raise NotFoundError("Part")
        await self.session.commit()

    async def _retire_previous(self, part: PartReplacement) -> None:
        """A newly installed part supersedes the installed one of the same type and position."""
        superseded: ColumnElement[bool] = PartReplacement.position.is_not_distinct_from(
            part.position
        )
        await self.session.execute(
            update(PartReplacement)
            .where(
                PartReplacement.vehicle_id == part.vehicle_id,
                PartReplacement.part_type_id == part.part_type_id,
                PartReplacement.id != part.id,
                PartReplacement.removed_date.is_(None),
                PartReplacement.installed_date <= part.installed_date,
                superseded,
            )
            .values(removed_date=part.installed_date, removed_mileage=part.installed_mileage)
            .execution_options(synchronize_session=False)
        )

    async def _advance_odometer(self, ctx: VehicleContext, part: PartReplacement) -> None:
        if part.installed_mileage is None:
            return
        vehicle = await self.mileage.lock_vehicle(ctx.vehicle_id)
        await self.mileage.record_odometer(
            vehicle, part.installed_mileage, part.installed_date, MileageSource.PART, ctx.user.id
        )

    async def _validate_references(
        self,
        ctx: VehicleContext,
        garage_id: uuid.UUID | None,
        maintenance_record_id: uuid.UUID | None,
    ) -> None:
        await ensure_garage_usable(self.session, ctx.user.id, garage_id)
        if maintenance_record_id is None:
            return
        exists = await self.session.scalar(
            select(MaintenanceRecord.id).where(
                MaintenanceRecord.id == maintenance_record_id,
                MaintenanceRecord.vehicle_id == ctx.vehicle_id,
            )
        )
        if exists is None:
            raise ValidationAppError(
                fields={"maintenance_record_id": "Unknown maintenance record for this vehicle."}
            )
