"""Declarative base, constraint naming convention and reusable column mixins."""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.ids import uuid7

# Deterministic constraint names keep Alembic revisions reproducible.
NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

MONEY = sa.Numeric(12, 2)
UNIT_PRICE = sa.Numeric(10, 4)


def utc_now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    metadata = sa.MetaData(naming_convention=NAMING_CONVENTION)
    type_annotation_map = {
        uuid.UUID: sa.Uuid(),
        datetime: sa.DateTime(timezone=True),
        date: sa.Date(),
        Decimal: MONEY,
        dict[str, Any]: JSONB(),
    }


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7, sort_order=-100)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        default=utc_now, server_default=sa.func.now(), sort_order=100
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=utc_now, onupdate=utc_now, server_default=sa.func.now(), sort_order=101
    )


class BaseModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Abstract base for entities: UUIDv7 primary key + created_at/updated_at."""

    __abstract__ = True


def str_enum(enum_cls: type[StrEnum], name: str, length: int = 20) -> sa.Enum:
    """Store a StrEnum as VARCHAR + CHECK constraint (easier to evolve than native enums)."""
    return sa.Enum(
        enum_cls,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=length,
        values_callable=lambda members: [member.value for member in members],
        validate_strings=True,
    )
