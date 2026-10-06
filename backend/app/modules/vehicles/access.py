"""Vehicle authorization: resolve the caller's role on a vehicle and guard routes.

A vehicle that does not exist and a vehicle the caller cannot see both produce 404, so
identifiers cannot be probed. A visible vehicle with an insufficient role produces 403.
"""

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import Depends
from sqlalchemy import ColumnElement, Select, and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, DbSession
from app.core.exceptions import ForbiddenError, NotFoundError
from app.modules.users.models import User
from app.modules.vehicles.models import Vehicle, VehicleAccess, VehicleRole


@dataclass(frozen=True, slots=True)
class VehicleContext:
    """The vehicle of the current route, the caller and the caller's role on it."""

    vehicle: Vehicle
    role: VehicleRole
    user: User

    @property
    def vehicle_id(self) -> uuid.UUID:
        return self.vehicle.id


async def resolve_vehicle_role(
    session: AsyncSession, vehicle_id: uuid.UUID, user_id: uuid.UUID, *, for_update: bool = False
) -> tuple[Vehicle, VehicleRole] | None:
    """Return the vehicle and the user's role on it, or None when not accessible (1 query)."""
    stmt = (
        select(Vehicle, VehicleAccess.role)
        .outerjoin(
            VehicleAccess,
            and_(VehicleAccess.vehicle_id == Vehicle.id, VehicleAccess.user_id == user_id),
        )
        .where(Vehicle.id == vehicle_id)
    )
    if for_update:
        stmt = stmt.with_for_update(of=Vehicle)
    row = (await session.execute(stmt)).one_or_none()
    if row is None:
        return None
    vehicle, shared_role = row
    if vehicle.owner_id == user_id:
        return vehicle, VehicleRole.OWNER
    if shared_role is None:
        return None
    return vehicle, VehicleRole(shared_role.value)


def accessible_vehicle_ids(user_id: uuid.UUID) -> Select[uuid.UUID]:
    """Select of vehicle ids visible to the user (owned or shared), for `IN` filters."""
    return (
        select(Vehicle.id)
        .outerjoin(
            VehicleAccess,
            and_(VehicleAccess.vehicle_id == Vehicle.id, VehicleAccess.user_id == user_id),
        )
        .where((Vehicle.owner_id == user_id) | VehicleAccess.id.is_not(None))
    )


def accessible_vehicles_clause(
    vehicle_column: Any, user_id: uuid.UUID, vehicle_id: uuid.UUID | None = None
) -> ColumnElement[bool]:
    """Restrict a `vehicle_id` column to the user's vehicles (optionally one of them)."""
    clause: ColumnElement[bool] = vehicle_column.in_(accessible_vehicle_ids(user_id))
    if vehicle_id is not None:
        clause = and_(clause, vehicle_column == vehicle_id)
    return clause


def require_vehicle_role(
    minimum: VehicleRole,
) -> Callable[[uuid.UUID, User, AsyncSession], Awaitable[VehicleContext]]:
    """Dependency factory guarding routes that have a `{vehicle_id}` path parameter."""

    async def dependency(
        vehicle_id: uuid.UUID, user: CurrentUser, session: DbSession
    ) -> VehicleContext:
        resolved = await resolve_vehicle_role(session, vehicle_id, user.id)
        if resolved is None:
            raise NotFoundError("Vehicle")
        vehicle, role = resolved
        if not role.allows(minimum):
            raise ForbiddenError(f"This action requires the '{minimum.value}' role on the vehicle.")
        return VehicleContext(vehicle=vehicle, role=role, user=user)

    return dependency


VehicleViewer = Annotated[VehicleContext, Depends(require_vehicle_role(VehicleRole.VIEWER))]
VehicleEditor = Annotated[VehicleContext, Depends(require_vehicle_role(VehicleRole.EDITOR))]
VehicleOwner = Annotated[VehicleContext, Depends(require_vehicle_role(VehicleRole.OWNER))]
