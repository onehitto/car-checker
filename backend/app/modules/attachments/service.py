"""Attachment use cases: upload, listing, download, deletion and the vehicle picture."""

import hashlib
import uuid
from collections.abc import AsyncIterator, Iterable
from dataclasses import dataclass
from typing import Any

from sqlalchemy import Select, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock
from app.core.config import Settings
from app.core.exceptions import NotFoundError, ValidationAppError
from app.core.ids import uuid7
from app.core.logging import get_logger
from app.core.pagination import Page, PageParams, paginate
from app.modules.attachments.models import Attachment, AttachmentEntity
from app.modules.attachments.storage import StorageBackend
from app.modules.attachments.validation import IMAGE_TYPES, validate_upload
from app.modules.documents.models import VehicleDocument
from app.modules.expenses.models import Expense
from app.modules.fuel.models import FuelRecord
from app.modules.maintenance.models import MaintenanceRecord
from app.modules.parts.models import PartReplacement
from app.modules.tires.models import Tire
from app.modules.vehicles.access import VehicleContext

logger = get_logger(__name__)

# Parent tables of attachments; every one of them has a `vehicle_id` column.
ENTITY_MODELS: dict[AttachmentEntity, Any] = {
    AttachmentEntity.MAINTENANCE_RECORD: MaintenanceRecord,
    AttachmentEntity.PART_REPLACEMENT: PartReplacement,
    AttachmentEntity.EXPENSE: Expense,
    AttachmentEntity.VEHICLE_DOCUMENT: VehicleDocument,
    AttachmentEntity.FUEL_RECORD: FuelRecord,
    AttachmentEntity.TIRE: Tire,
}


@dataclass(frozen=True, slots=True)
class UploadedFile:
    file_name: str | None
    content: bytes


async def storage_keys_for_vehicles(
    session: AsyncSession, vehicle_ids: Select[Any] | Iterable[uuid.UUID]
) -> list[str]:
    """Keys of every stored file of these vehicles (collected before deleting them)."""
    keys = await session.scalars(
        select(Attachment.storage_key).where(Attachment.vehicle_id.in_(vehicle_ids))
    )
    return list(keys)


async def delete_stored_files(storage: StorageBackend, keys: Iterable[str]) -> None:
    """Best effort, after the transaction committed; leftovers are removed by the cleanup job."""
    for key in keys:
        try:
            await storage.delete(key)
        except Exception as exc:  # noqa: BLE001 - never fail the request after commit
            logger.warning("file_delete_failed", error=type(exc).__name__)


class AttachmentService:
    def __init__(
        self, session: AsyncSession, storage: StorageBackend, settings: Settings, clock: Clock
    ) -> None:
        self.session = session
        self.storage = storage
        self.settings = settings
        self.clock = clock

    async def list_attachments(
        self,
        ctx: VehicleContext,
        entity_type: AttachmentEntity | None,
        entity_id: uuid.UUID | None,
        params: PageParams,
    ) -> Page[Attachment]:
        stmt = select(Attachment).where(Attachment.vehicle_id == ctx.vehicle_id)
        if entity_type:
            stmt = stmt.where(Attachment.entity_type == entity_type)
        if entity_id:
            stmt = stmt.where(Attachment.entity_id == entity_id)
        stmt = stmt.order_by(Attachment.uploaded_at.desc(), Attachment.id.desc())
        return await paginate(self.session, stmt, params)

    async def get(self, ctx: VehicleContext, attachment_id: uuid.UUID) -> Attachment:
        attachment = await self.session.scalar(
            select(Attachment).where(
                Attachment.id == attachment_id, Attachment.vehicle_id == ctx.vehicle_id
            )
        )
        if attachment is None:
            raise NotFoundError("Attachment")
        return attachment

    async def open(
        self, ctx: VehicleContext, attachment_id: uuid.UUID
    ) -> tuple[Attachment, AsyncIterator[bytes]]:
        attachment = await self.get(ctx, attachment_id)
        return attachment, self.storage.open(attachment.storage_key)

    async def upload(
        self,
        ctx: VehicleContext,
        entity_type: AttachmentEntity,
        entity_id: uuid.UUID | None,
        file: UploadedFile,
    ) -> Attachment:
        resolved_id = await self._resolve_entity(ctx, entity_type, entity_id)
        attachment = await self._store(ctx, entity_type, resolved_id, file)
        await self.session.commit()
        return attachment

    async def delete(self, ctx: VehicleContext, attachment_id: uuid.UUID) -> None:
        attachment = await self.get(ctx, attachment_id)
        await self.session.execute(delete(Attachment).where(Attachment.id == attachment.id))
        await self.session.commit()
        await delete_stored_files(self.storage, [attachment.storage_key])

    async def set_vehicle_image(self, ctx: VehicleContext, file: UploadedFile) -> Attachment:
        previous = ctx.vehicle.image_attachment_id
        attachment = await self._store(
            ctx, AttachmentEntity.VEHICLE, ctx.vehicle_id, file, allowed=IMAGE_TYPES
        )
        ctx.vehicle.image_attachment_id = attachment.id
        old_keys = await self._delete_rows([previous] if previous else [])
        await self.session.commit()
        await delete_stored_files(self.storage, old_keys)
        return attachment

    async def remove_vehicle_image(self, ctx: VehicleContext) -> None:
        previous = ctx.vehicle.image_attachment_id
        if previous is None:
            raise NotFoundError("Vehicle image")
        ctx.vehicle.image_attachment_id = None
        old_keys = await self._delete_rows([previous])
        await self.session.commit()
        await delete_stored_files(self.storage, old_keys)

    async def _store(
        self,
        ctx: VehicleContext,
        entity_type: AttachmentEntity,
        entity_id: uuid.UUID,
        file: UploadedFile,
        allowed: frozenset[str] | None = None,
    ) -> Attachment:
        validated = validate_upload(
            file.content, file.file_name, self.settings.max_upload_size, allowed
        )
        now = self.clock.now()
        key = f"{ctx.vehicle_id}/{now:%Y}/{now:%m}/{uuid7().hex}.{validated.extension}"
        await self.storage.save(key, validated.content)
        attachment = Attachment(
            user_id=ctx.user.id,
            vehicle_id=ctx.vehicle_id,
            entity_type=entity_type,
            entity_id=entity_id,
            file_name=validated.file_name,
            content_type=validated.content_type,
            file_size=validated.size,
            storage_backend=self.storage.name,
            storage_key=key,
            checksum_sha256=hashlib.sha256(validated.content).hexdigest(),
            uploaded_at=now,
        )
        self.session.add(attachment)
        try:
            await self.session.flush()
        except Exception:
            await delete_stored_files(self.storage, [key])
            raise
        logger.info("file_uploaded", attachment_id=str(attachment.id), size=validated.size)
        return attachment

    async def _delete_rows(self, attachment_ids: list[uuid.UUID]) -> list[str]:
        if not attachment_ids:
            return []
        keys = await self.session.scalars(
            delete(Attachment)
            .where(Attachment.id.in_(attachment_ids))
            .returning(Attachment.storage_key)
        )
        return list(keys)

    async def _resolve_entity(
        self, ctx: VehicleContext, entity_type: AttachmentEntity, entity_id: uuid.UUID | None
    ) -> uuid.UUID:
        """The parent record must exist on the same vehicle (ids are never trusted)."""
        if entity_type is AttachmentEntity.VEHICLE:
            if entity_id not in (None, ctx.vehicle_id):
                raise ValidationAppError(fields={"entity_id": "Must be the vehicle id."})
            return ctx.vehicle_id
        if entity_id is None:
            raise ValidationAppError(fields={"entity_id": "Required for this entity type."})
        model = ENTITY_MODELS[entity_type]
        exists = await self.session.scalar(
            select(model.id).where(model.id == entity_id, model.vehicle_id == ctx.vehicle_id)
        )
        if exists is None:
            raise ValidationAppError(
                fields={"entity_id": f"Unknown {entity_type.value} for this vehicle."}
            )
        return entity_id
