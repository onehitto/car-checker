"""Profile, session management and account deletion."""

import asyncio
import uuid

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock
from app.core.exceptions import NotFoundError, ValidationAppError
from app.core.logging import get_logger
from app.core.security import verify_password
from app.core.updates import apply_updates
from app.modules.attachments.service import delete_stored_files, storage_keys_for_vehicles
from app.modules.attachments.storage import StorageBackend
from app.modules.audit.service import RequestMeta, record_audit
from app.modules.auth.models import UserSession
from app.modules.users.models import User
from app.modules.users.schemas import SessionResponse, UserUpdate
from app.modules.vehicles.models import Vehicle

logger = get_logger(__name__)

REQUIRED_PROFILE_FIELDS = frozenset(UserUpdate.model_fields) - {"phone_number"}


class UserService:
    def __init__(self, session: AsyncSession, clock: Clock) -> None:
        self.session = session
        self.clock = clock

    async def update_profile(self, user: User, data: UserUpdate) -> User:
        apply_updates(user, data, required=REQUIRED_PROFILE_FIELDS)
        await self.session.commit()
        return user

    async def delete_account(
        self,
        user: User,
        password: str,
        meta: RequestMeta,
        storage: StorageBackend | None = None,
    ) -> None:
        if not await asyncio.to_thread(verify_password, user.password_hash, password):
            raise ValidationAppError(fields={"password": "Password is incorrect."})
        user_id = user.id
        file_keys = await storage_keys_for_vehicles(
            self.session, select(Vehicle.id).where(Vehicle.owner_id == user_id)
        )
        # The audit entry outlives the account; it only keeps the pseudonymous id.
        record_audit(
            self.session,
            "user.deleted",
            user_id=None,
            meta=meta,
            entity_type="user",
            entity_id=user_id,
        )
        # Vehicles and every vehicle record are removed by ON DELETE CASCADE.
        await self.session.execute(delete(User).where(User.id == user_id))
        await self.session.commit()
        if storage is not None:
            await delete_stored_files(storage, file_keys)
        logger.info("user_deleted", user_id=str(user_id))

    async def list_sessions(
        self, user_id: uuid.UUID, current_session_id: uuid.UUID
    ) -> list[SessionResponse]:
        sessions = await self.session.scalars(
            select(UserSession)
            .where(
                UserSession.user_id == user_id,
                UserSession.revoked_at.is_(None),
                UserSession.expires_at > self.clock.now(),
            )
            .order_by(UserSession.last_used_at.desc())
        )
        return [
            SessionResponse.model_validate(
                {
                    "id": s.id,
                    "user_agent": s.user_agent,
                    "ip_address": s.ip_address,
                    "created_at": s.created_at,
                    "last_used_at": s.last_used_at,
                    "expires_at": s.expires_at,
                    "current": s.id == current_session_id,
                }
            )
            for s in sessions
        ]

    async def revoke_session(
        self, user_id: uuid.UUID, session_id: uuid.UUID, meta: RequestMeta
    ) -> None:
        result = await self.session.execute(
            update(UserSession)
            .where(
                UserSession.id == session_id,
                UserSession.user_id == user_id,
                UserSession.revoked_at.is_(None),
            )
            .values(revoked_at=self.clock.now())
        )
        if result.rowcount == 0:  # type: ignore[attr-defined]
            raise NotFoundError("Session")
        record_audit(
            self.session,
            "auth.session_revoked",
            user_id=user_id,
            meta=meta,
            entity_type="user_session",
            entity_id=session_id,
        )
        await self.session.commit()
