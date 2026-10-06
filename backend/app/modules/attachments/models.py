"""File attachments (invoices, receipts, photos, certificates...)."""

import uuid
from datetime import datetime
from enum import StrEnum

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel, StrEnumType, enum_check, utc_now
from app.modules.vehicles.models import Vehicle


class AttachmentEntity(StrEnum):
    """Kind of record a file is attached to (always within one vehicle)."""

    VEHICLE = "vehicle"
    MAINTENANCE_RECORD = "maintenance_record"
    PART_REPLACEMENT = "part_replacement"
    EXPENSE = "expense"
    VEHICLE_DOCUMENT = "vehicle_document"
    FUEL_RECORD = "fuel_record"
    TIRE = "tire"


class Attachment(BaseModel):
    __tablename__ = "attachments"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.ForeignKey("users.id", ondelete="SET NULL")
    )
    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("vehicles.id", ondelete="CASCADE"), index=True
    )
    entity_type: Mapped[AttachmentEntity] = mapped_column(StrEnumType(AttachmentEntity, length=30))
    entity_id: Mapped[uuid.UUID]
    file_name: Mapped[str] = mapped_column(sa.String(255))
    content_type: Mapped[str] = mapped_column(sa.String(100))
    file_size: Mapped[int] = mapped_column(sa.BigInteger)
    storage_backend: Mapped[str] = mapped_column(sa.String(20))
    storage_key: Mapped[str] = mapped_column(sa.String(500), unique=True)
    checksum_sha256: Mapped[str] = mapped_column(sa.CHAR(64))
    uploaded_at: Mapped[datetime] = mapped_column(default=utc_now, server_default=sa.func.now())

    vehicle: Mapped[Vehicle] = relationship(lazy="raise", foreign_keys=[vehicle_id])

    __table_args__ = (
        enum_check("entity_type", AttachmentEntity),
        sa.CheckConstraint("file_size > 0", name="file_size_positive"),
        sa.Index(None, "entity_type", "entity_id"),
    )
