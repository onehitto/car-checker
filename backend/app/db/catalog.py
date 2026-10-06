"""Shared shape of type catalogs (maintenance types, part types).

A catalog row is either a *system* type (`user_id IS NULL`, identified by a stable `code`
used for translations and seeds) or a *custom* type created by one user.
"""

import uuid
from typing import Any

import sqlalchemy as sa
from pydantic import BaseModel, ConfigDict, model_validator
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.schema import SchemaItem

from app.core.i18n import Language, has_translation, translate


def catalog_table_args(table: str) -> tuple[SchemaItem, ...]:
    """Constraints of a catalog table: unique system codes, unique custom names per user."""
    return (
        sa.Index(
            f"uq_{table}_code", "code", unique=True, postgresql_where=sa.text("user_id IS NULL")
        ),
        sa.Index(
            f"uq_{table}_user_id_name",
            "user_id",
            "name",
            unique=True,
            postgresql_where=sa.text("user_id IS NOT NULL"),
        ),
        sa.CheckConstraint("user_id IS NOT NULL OR code IS NOT NULL", name="system_type_has_code"),
    )


class CatalogTypeMixin:
    """Columns common to catalog tables. Concrete tables add their default intervals."""

    translation_prefix: str = ""

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    code: Mapped[str | None] = mapped_column(sa.String(50))
    name: Mapped[str] = mapped_column(sa.String(100))
    description: Mapped[str | None] = mapped_column(sa.Text)

    @property
    def is_system(self) -> bool:
        return self.user_id is None

    def localized_name(self, language: Language | str | None = None) -> str:
        """System types are translated from their code; custom types keep the user's name.

        Without `language`, the current request/job language is used.
        """
        if self.code and self.is_system:
            key = f"{self.translation_prefix}.{self.code}"
            if has_translation(key, language):
                return translate(key, language)
        return self.name


class CatalogResponseModel(BaseModel):
    """Response schema of a catalog row; `name` is localized for system types."""

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def _localize_name(cls, value: Any) -> Any:
        if isinstance(value, CatalogTypeMixin):
            fields = {
                name: getattr(value, name) for name in cls.model_fields if hasattr(value, name)
            }
            fields["name"] = value.localized_name()
            return fields
        return value
