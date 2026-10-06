"""User accounts."""

from datetime import datetime
from enum import StrEnum

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.core.i18n import Language
from app.core.units import ConsumptionUnit, DistanceUnit
from app.db.base import BaseModel, StrEnumType, enum_check


class UserRole(StrEnum):
    USER = "user"
    ADMIN = "admin"


class User(BaseModel):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(sa.String(320), unique=True)
    password_hash: Mapped[str] = mapped_column(sa.String(255))
    first_name: Mapped[str] = mapped_column(sa.String(100))
    last_name: Mapped[str] = mapped_column(sa.String(100))
    phone_number: Mapped[str | None] = mapped_column(sa.String(32))

    preferred_language: Mapped[Language] = mapped_column(
        StrEnumType(Language, length=5),
        default=Language.EN,
        server_default=Language.EN.value,
    )
    preferred_currency: Mapped[str] = mapped_column(sa.CHAR(3), default="EUR", server_default="EUR")
    preferred_distance_unit: Mapped[DistanceUnit] = mapped_column(
        StrEnumType(DistanceUnit, length=2),
        default=DistanceUnit.KM,
        server_default=DistanceUnit.KM.value,
    )
    preferred_consumption_unit: Mapped[ConsumptionUnit] = mapped_column(
        StrEnumType(ConsumptionUnit, length=10),
        default=ConsumptionUnit.L_100KM,
        server_default=ConsumptionUnit.L_100KM.value,
    )
    timezone: Mapped[str] = mapped_column(sa.String(64), default="UTC", server_default="UTC")

    role: Mapped[UserRole] = mapped_column(
        StrEnumType(UserRole),
        default=UserRole.USER,
        server_default=UserRole.USER.value,
    )
    is_active: Mapped[bool] = mapped_column(default=True, server_default=sa.true())
    email_verified_at: Mapped[datetime | None]
    last_login_at: Mapped[datetime | None]
    password_changed_at: Mapped[datetime | None]

    __table_args__ = (
        sa.CheckConstraint("email = lower(email)", name="email_lowercase"),
        enum_check("preferred_language", Language),
        enum_check("preferred_distance_unit", DistanceUnit),
        enum_check("preferred_consumption_unit", ConsumptionUnit),
        enum_check("role", UserRole),
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()
