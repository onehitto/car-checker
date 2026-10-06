"""Garages, mechanics, dealerships and other service providers saved by a user."""

import uuid
from enum import StrEnum

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel, StrEnumType, enum_check
from app.modules.users.models import User


class GarageType(StrEnum):
    GARAGE = "garage"
    MECHANIC = "mechanic"
    DEALERSHIP = "dealership"
    TIRE_SHOP = "tire_shop"
    BODY_SHOP = "body_shop"
    INSPECTION_CENTER = "inspection_center"
    OTHER = "other"


class Garage(BaseModel):
    __tablename__ = "garages"

    user_id: Mapped[uuid.UUID] = mapped_column(sa.ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(sa.String(120))
    garage_type: Mapped[GarageType] = mapped_column(
        StrEnumType(GarageType), default=GarageType.GARAGE, server_default=GarageType.GARAGE.value
    )
    contact_name: Mapped[str | None] = mapped_column(sa.String(120))
    phone: Mapped[str | None] = mapped_column(sa.String(32))
    email: Mapped[str | None] = mapped_column(sa.String(320))
    address: Mapped[str | None] = mapped_column(sa.String(255))
    city: Mapped[str | None] = mapped_column(sa.String(100))
    country: Mapped[str | None] = mapped_column(sa.String(100))
    website: Mapped[str | None] = mapped_column(sa.String(255))
    notes: Mapped[str | None] = mapped_column(sa.Text)

    user: Mapped[User] = relationship(lazy="raise")

    __table_args__ = (
        enum_check("garage_type", GarageType),
        sa.Index(None, "user_id", "name"),
    )
