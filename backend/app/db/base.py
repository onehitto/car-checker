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

    def __init__(self, **kwargs: Any) -> None:
        # Assign the id at construction (not at flush) so related rows can reference it at once.
        kwargs.setdefault("id", uuid7())
        super().__init__(**kwargs)


class StrEnumType(sa.types.TypeDecorator[Any]):
    """StrEnum stored as VARCHAR. Pair every column with `enum_check()` in `__table_args__`.

    VARCHAR + CHECK is easier to evolve than native PostgreSQL enum types: adding a value is
    a constraint swap inside a regular transactional migration.
    """

    impl = sa.String
    cache_ok = True

    def __init__(self, enum_cls: type[StrEnum], length: int = 20) -> None:
        super().__init__(length)
        self.enum_cls = enum_cls

    def process_bind_param(self, value: Any, dialect: sa.Dialect) -> str | None:
        return None if value is None else self.enum_cls(value).value

    def process_result_value(self, value: Any, dialect: sa.Dialect) -> StrEnum | None:
        return None if value is None else self.enum_cls(value)


def enum_check(column: str, enum_cls: type[StrEnum]) -> sa.CheckConstraint:
    """CHECK constraint restricting `column` to the enum values (named ck_<table>_<column>)."""
    values = ", ".join(f"'{member.value}'" for member in enum_cls)
    return sa.CheckConstraint(f"{column} IN ({values})", name=column)
