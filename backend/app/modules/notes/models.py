"""Free-text notes about a vehicle or one of its records."""

import uuid
from enum import StrEnum

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel, StrEnumType, enum_check
from app.modules.vehicles.models import Vehicle


class NoteCategory(StrEnum):
    GENERAL = "general"
    MAINTENANCE = "maintenance"
    REPAIR = "repair"
    PART = "part"
    PROBLEM = "problem"
    DOCUMENT = "document"


class NoteEntity(StrEnum):
    MAINTENANCE_RECORD = "maintenance_record"
    PART_REPLACEMENT = "part_replacement"
    EXPENSE = "expense"
    VEHICLE_DOCUMENT = "vehicle_document"
    FUEL_RECORD = "fuel_record"
    TIRE = "tire"


class Note(BaseModel):
    __tablename__ = "notes"

    vehicle_id: Mapped[uuid.UUID] = mapped_column(sa.ForeignKey("vehicles.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.ForeignKey("users.id", ondelete="SET NULL")
    )
    entity_type: Mapped[NoteEntity | None] = mapped_column(StrEnumType(NoteEntity, length=30))
    entity_id: Mapped[uuid.UUID | None]
    category: Mapped[NoteCategory] = mapped_column(
        StrEnumType(NoteCategory),
        default=NoteCategory.GENERAL,
        server_default=NoteCategory.GENERAL.value,
    )
    title: Mapped[str | None] = mapped_column(sa.String(200))
    body: Mapped[str] = mapped_column(sa.Text)
    is_pinned: Mapped[bool] = mapped_column(default=False, server_default=sa.false())

    vehicle: Mapped[Vehicle] = relationship(lazy="raise")

    __table_args__ = (
        enum_check("entity_type", NoteEntity),
        enum_check("category", NoteCategory),
        sa.CheckConstraint(
            "(entity_type IS NULL) = (entity_id IS NULL)", name="entity_type_and_id_together"
        ),
        sa.Index(None, "vehicle_id", "created_at"),
        sa.Index(None, "entity_type", "entity_id"),
    )
