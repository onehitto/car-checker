"""Vehicle sharing: the owner grants `editor` or `viewer` access to other users."""

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.clock import Clock
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationAppError
from app.modules.alerts.engine import AlertEngine
from app.modules.audit.service import RequestMeta, record_audit
from app.modules.users.models import User
from app.modules.vehicles.access import VehicleContext
from app.modules.vehicles.models import VehicleAccess, VehicleRole
from app.modules.vehicles.schemas import ShareCreate, ShareUpdate


class SharingService:
    def __init__(self, session: AsyncSession, clock: Clock) -> None:
        self.session = session
        self.alerts = AlertEngine(session, clock)

    async def list_shares(self, ctx: VehicleContext) -> Sequence[VehicleAccess]:
        return (
            await self.session.scalars(
                select(VehicleAccess)
                .options(joinedload(VehicleAccess.user))
                .where(VehicleAccess.vehicle_id == ctx.vehicle_id)
                .order_by(VehicleAccess.created_at)
            )
        ).all()

    async def _get(self, ctx: VehicleContext, access_id: uuid.UUID) -> VehicleAccess:
        access = await self.session.scalar(
            select(VehicleAccess)
            .options(joinedload(VehicleAccess.user))
            .where(VehicleAccess.id == access_id, VehicleAccess.vehicle_id == ctx.vehicle_id)
            .execution_options(populate_existing=True)
        )
        if access is None:
            raise NotFoundError("Share")
        return access

    async def share(
        self, ctx: VehicleContext, data: ShareCreate, meta: RequestMeta
    ) -> VehicleAccess:
        grantee = await self.session.scalar(
            select(User).where(User.email == data.email.lower(), User.is_active)
        )
        if grantee is None:
            raise NotFoundError(message="No Car Checker account uses this e-mail address.")
        if grantee.id == ctx.vehicle.owner_id:
            raise ValidationAppError(fields={"email": "The owner already has full access."})
        existing = await self.session.scalar(
            select(VehicleAccess.id).where(
                VehicleAccess.vehicle_id == ctx.vehicle_id, VehicleAccess.user_id == grantee.id
            )
        )
        if existing:
            raise ConflictError(
                "The vehicle is already shared with this user.", code="ALREADY_SHARED"
            )
        access = VehicleAccess(
            vehicle_id=ctx.vehicle_id, user_id=grantee.id, role=data.role, granted_by_id=ctx.user.id
        )
        self.session.add(access)
        self._audit(ctx, "vehicle.shared", meta, grantee.id, data.role.value)
        await self.alerts.sync_vehicle(ctx.vehicle_id)
        await self.session.commit()
        return await self._get(ctx, access.id)

    async def update(
        self, ctx: VehicleContext, access_id: uuid.UUID, data: ShareUpdate, meta: RequestMeta
    ) -> VehicleAccess:
        access = await self._get(ctx, access_id)
        access.role = data.role
        self._audit(ctx, "vehicle.share_updated", meta, access.user_id, data.role.value)
        await self.alerts.sync_vehicle(ctx.vehicle_id)
        await self.session.commit()
        return await self._get(ctx, access.id)

    async def revoke(self, ctx: VehicleContext, access_id: uuid.UUID, meta: RequestMeta) -> None:
        """The owner revokes any share; a grantee may remove their own access (leave)."""
        access = await self._get(ctx, access_id)
        if ctx.role is not VehicleRole.OWNER and access.user_id != ctx.user.id:
            raise ForbiddenError("Only the owner can revoke someone else's access.")
        await self.session.delete(access)
        self._audit(ctx, "vehicle.share_revoked", meta, access.user_id, access.role.value)
        await self.alerts.sync_vehicle(ctx.vehicle_id)
        await self.session.commit()

    def _audit(
        self,
        ctx: VehicleContext,
        action: str,
        meta: RequestMeta,
        grantee_id: uuid.UUID,
        role: str,
    ) -> None:
        record_audit(
            self.session,
            action,
            user_id=ctx.user.id,
            meta=meta,
            entity_type="vehicle",
            entity_id=ctx.vehicle_id,
            details={"grantee_id": str(grantee_id), "role": role},
        )
