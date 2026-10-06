"""Generic use cases for type catalogs (shared by maintenance types and part types)."""

import uuid
from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel as Schema
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationAppError
from app.core.pagination import like_pattern
from app.core.updates import apply_updates
from app.db.catalog import CatalogTypeMixin


class CatalogService[M: CatalogTypeMixin]:
    """System types are visible to everyone and read-only; custom types belong to one user."""

    def __init__(self, session: AsyncSession, model: type[M], resource: str) -> None:
        self.session = session
        self.model = model
        self.resource = resource

    def _visible_to(self, user_id: uuid.UUID) -> Any:
        return or_(self.model.user_id.is_(None), self.model.user_id == user_id)

    async def list_types(
        self, user_id: uuid.UUID, *, q: str | None = None, category: str | None = None
    ) -> Sequence[M]:
        model: Any = self.model
        stmt = select(model).where(self._visible_to(user_id))
        if category:
            stmt = stmt.where(model.category == category)
        if q:
            stmt = stmt.where(model.name.ilike(like_pattern(q), escape="\\"))
        stmt = stmt.order_by(model.user_id.is_not(None), model.name)
        return (await self.session.scalars(stmt)).all()

    async def get_visible(self, user_id: uuid.UUID, type_id: uuid.UUID) -> M:
        model: Any = self.model
        found = await self.session.scalar(
            select(model).where(model.id == type_id, self._visible_to(user_id))
        )
        if found is None:
            raise NotFoundError(self.resource)
        return found  # type: ignore[no-any-return]

    async def resolve_reference(self, user_id: uuid.UUID, type_id: uuid.UUID, field: str) -> M:
        """Validate a type id sent in a request body."""
        try:
            return await self.get_visible(user_id, type_id)
        except NotFoundError:
            raise ValidationAppError(fields={field: f"Unknown {self.resource.lower()}."}) from None

    async def create(self, user_id: uuid.UUID, data: Schema) -> M:
        values = data.model_dump()
        await self._ensure_name_available(user_id, values["name"])
        model: Any = self.model
        item = model(user_id=user_id, **values)
        self.session.add(item)
        await self.session.commit()
        return item  # type: ignore[no-any-return]

    async def update(self, user_id: uuid.UUID, type_id: uuid.UUID, data: Schema) -> M:
        item = await self._get_owned(user_id, type_id)
        new_name = data.model_dump(exclude_unset=True).get("name")
        if new_name and new_name != item.name:
            await self._ensure_name_available(user_id, new_name)
        apply_updates(item, data, required={"name", "category"})
        await self.session.commit()
        return item

    async def delete(self, user_id: uuid.UUID, type_id: uuid.UUID) -> None:
        item = await self._get_owned(user_id, type_id)
        await self.session.delete(item)
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise ConflictError(
                f"This {self.resource.lower()} is used by existing records.", code="TYPE_IN_USE"
            ) from None

    async def _get_owned(self, user_id: uuid.UUID, type_id: uuid.UUID) -> M:
        item = await self.get_visible(user_id, type_id)
        if item.is_system:
            raise ForbiddenError(f"System {self.resource.lower()}s cannot be modified.")
        return item

    async def _ensure_name_available(self, user_id: uuid.UUID, name: str) -> None:
        model: Any = self.model
        exists = await self.session.scalar(
            select(model.id).where(model.user_id == user_id, model.name == name)
        )
        if exists:
            raise ConflictError(f"You already have a {self.resource.lower()} named '{name}'.")
