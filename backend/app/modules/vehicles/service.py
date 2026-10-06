"""Vehicle use cases."""

import uuid
from dataclasses import dataclass

from sqlalchemy import and_, case, delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock
from app.core.exceptions import ConflictError, ValidationAppError
from app.core.pagination import Page, PageParams, apply_sort, like_pattern, paginate_rows
from app.core.schemas import ensure_not_future
from app.core.updates import apply_updates
from app.modules.alerts.engine import AlertEngine
from app.modules.audit.service import RequestMeta, record_audit
from app.modules.mileage.service import MileageService
from app.modules.users.models import User
from app.modules.vehicles.access import VehicleContext
from app.modules.vehicles.models import Vehicle, VehicleAccess, VehicleRole, VehicleStatus
from app.modules.vehicles.schemas import (
    VehicleCreate,
    VehicleResponse,
    VehicleUpdate,
)

VEHICLE_SORT_FIELDS = {
    "created_at": Vehicle.created_at,
    "updated_at": Vehicle.updated_at,
    "brand": Vehicle.brand,
    "model": Vehicle.model,
    "year": Vehicle.year,
    "current_mileage": Vehicle.current_mileage,
}
REQUIRED_FIELDS = frozenset(
    {"brand", "model", "year", "fuel_type", "currency", "initial_mileage", "status"}
)


@dataclass(frozen=True, slots=True)
class VehicleFilters:
    status: VehicleStatus | None = None
    role: VehicleRole | None = None
    q: str | None = None
    sort: str | None = None


def to_response(vehicle: Vehicle, role: VehicleRole) -> VehicleResponse:
    return VehicleResponse.model_validate(vehicle).model_copy(update={"access_role": role})


class VehicleService:
    def __init__(self, session: AsyncSession, clock: Clock) -> None:
        self.session = session
        self.clock = clock
        self.alerts = AlertEngine(session, clock)

    async def list_for_user(
        self, user: User, filters: VehicleFilters, params: PageParams
    ) -> Page[VehicleResponse]:
        role = case(
            (Vehicle.owner_id == user.id, VehicleRole.OWNER.value), else_=VehicleAccess.role
        ).label("role")
        stmt = (
            select(Vehicle, role)
            .outerjoin(
                VehicleAccess,
                and_(VehicleAccess.vehicle_id == Vehicle.id, VehicleAccess.user_id == user.id),
            )
            .where(or_(Vehicle.owner_id == user.id, VehicleAccess.id.is_not(None)))
        )
        if filters.status:
            stmt = stmt.where(Vehicle.status == filters.status)
        if filters.role is VehicleRole.OWNER:
            stmt = stmt.where(Vehicle.owner_id == user.id)
        elif filters.role:
            stmt = stmt.where(VehicleAccess.role == filters.role.value)
        if filters.q:
            pattern = like_pattern(filters.q)
            stmt = stmt.where(
                or_(
                    *(
                        column.ilike(pattern, escape="\\")
                        for column in (
                            Vehicle.brand,
                            Vehicle.model,
                            Vehicle.nickname,
                            Vehicle.license_plate,
                            Vehicle.vin,
                        )
                    )
                )
            )
        stmt = apply_sort(stmt, filters.sort, VEHICLE_SORT_FIELDS, "-created_at", Vehicle.id)
        page = await paginate_rows(self.session, stmt, params)
        return page.map(lambda row: to_response(row[0], VehicleRole(str(row[1]))))

    async def accessible_vehicles(
        self, user: User, status: VehicleStatus | None = None
    ) -> list[tuple[Vehicle, VehicleRole]]:
        """Every vehicle the user owns or that is shared with them, with their role."""
        stmt = (
            select(Vehicle, VehicleAccess.role)
            .outerjoin(
                VehicleAccess,
                and_(VehicleAccess.vehicle_id == Vehicle.id, VehicleAccess.user_id == user.id),
            )
            .where(or_(Vehicle.owner_id == user.id, VehicleAccess.id.is_not(None)))
            .order_by(Vehicle.created_at)
        )
        if status is not None:
            stmt = stmt.where(Vehicle.status == status)
        rows = (await self.session.execute(stmt)).all()
        return [
            (
                vehicle,
                VehicleRole.OWNER
                if vehicle.owner_id == user.id
                else VehicleRole(shared_role.value),
            )
            for vehicle, shared_role in rows
        ]

    async def create(self, owner: User, data: VehicleCreate) -> Vehicle:
        self._validate_dates_and_year(data.year, data.purchase_date)
        if data.vin:
            await self._ensure_vin_available(owner.id, data.vin)

        values = data.model_dump(exclude={"currency", "current_mileage"})
        vehicle = Vehicle(
            **values,
            owner_id=owner.id,
            currency=data.currency or owner.preferred_currency,
            current_mileage=(
                data.current_mileage if data.current_mileage is not None else data.initial_mileage
            ),
        )
        self.session.add(vehicle)
        today = self.clock.today(owner.timezone)
        self.session.add_all(MileageService.initial_entries(vehicle, today, owner.id))
        await self.session.commit()
        return vehicle

    async def update(self, ctx: VehicleContext, data: VehicleUpdate) -> Vehicle:
        vehicle = ctx.vehicle
        changes = data.model_dump(exclude_unset=True)
        self._validate_dates_and_year(changes.get("year"), changes.get("purchase_date"))
        if changes.get("vin") and changes["vin"] != vehicle.vin:
            await self._ensure_vin_available(vehicle.owner_id, changes["vin"])
        initial = changes.get("initial_mileage")
        if initial is not None and initial > vehicle.current_mileage:
            raise ValidationAppError(
                fields={"initial_mileage": "Cannot exceed the current mileage of the vehicle."}
            )
        apply_updates(vehicle, data, required=REQUIRED_FIELDS)
        await self.alerts.sync_vehicle(vehicle.id)
        await self.session.commit()
        return vehicle

    async def delete(self, ctx: VehicleContext, meta: RequestMeta) -> None:
        vehicle = ctx.vehicle
        record_audit(
            self.session,
            "vehicle.deleted",
            user_id=ctx.user.id,
            meta=meta,
            entity_type="vehicle",
            entity_id=vehicle.id,
            details={"name": vehicle.display_name},
        )
        await self.session.execute(delete(Vehicle).where(Vehicle.id == vehicle.id))
        await self.session.commit()

    def _validate_dates_and_year(self, year: int | None, purchase_date: object) -> None:
        today = self.clock.today()
        if year is not None and year > today.year + 1:
            raise ValidationAppError(fields={"year": f"Year cannot be after {today.year + 1}."})
        if purchase_date is not None:
            ensure_not_future(purchase_date, today, "purchase_date")  # type: ignore[arg-type]

    async def _ensure_vin_available(self, owner_id: uuid.UUID, vin: str) -> None:
        exists = await self.session.scalar(
            select(Vehicle.id).where(Vehicle.owner_id == owner_id, Vehicle.vin == vin)
        )
        if exists:
            raise ConflictError(
                "You already have a vehicle with this VIN.", code="VIN_ALREADY_REGISTERED"
            )
