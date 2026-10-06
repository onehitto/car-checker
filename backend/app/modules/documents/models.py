"""Vehicle documents (insurance, registration, inspection...)."""

import uuid
from datetime import date
from enum import StrEnum

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel, StrEnumType, enum_check
from app.modules.documents.expiration import DEFAULT_REMINDER_DAYS
from app.modules.vehicles.models import Vehicle


class DocumentType(StrEnum):
    INSURANCE = "insurance"
    REGISTRATION = "registration"
    TECHNICAL_INSPECTION = "technical_inspection"
    ROAD_TAX = "road_tax"
    WARRANTY = "warranty"
    LEASING = "leasing"
    OTHER = "other"


class VehicleDocument(BaseModel):
    __tablename__ = "vehicle_documents"

    vehicle_id: Mapped[uuid.UUID] = mapped_column(sa.ForeignKey("vehicles.id", ondelete="CASCADE"))
    document_type: Mapped[DocumentType] = mapped_column(StrEnumType(DocumentType, length=30))
    title: Mapped[str] = mapped_column(sa.String(150))
    document_number: Mapped[str | None] = mapped_column(sa.String(80))
    issue_date: Mapped[date | None]
    expiration_date: Mapped[date | None] = mapped_column(index=True)
    provider: Mapped[str | None] = mapped_column(sa.String(120))
    # Days before expiration at which reminders fire, stored largest first.
    reminder_days: Mapped[list[int]] = mapped_column(
        ARRAY(sa.Integer),
        default=lambda: list(DEFAULT_REMINDER_DAYS),
        server_default=sa.text("'{30,7,1,0}'"),
    )
    notes: Mapped[str | None] = mapped_column(sa.Text)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.ForeignKey("users.id", ondelete="SET NULL")
    )

    vehicle: Mapped[Vehicle] = relationship(lazy="raise")

    __table_args__ = (
        enum_check("document_type", DocumentType),
        sa.CheckConstraint(
            "expiration_date IS NULL OR issue_date IS NULL OR expiration_date >= issue_date",
            name="expiration_after_issue",
        ),
        sa.Index(None, "vehicle_id", "expiration_date"),
    )
