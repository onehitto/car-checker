"""Garage use cases. Garages are private to the user who saved them."""

import uuid
from dataclasses import dataclass

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationAppError
from app.core.pagination import Page, PageParams, apply_sort, like_pattern, paginate
from app.core.updates import apply_updates
from app.modules.garages.models import Garage, GarageType
from app.modules.garages.schemas import GarageCreate, GarageUpdate

GARAGE_SORT_FIELDS = {"name": Garage.name, "city": Garage.city, "created_at": Garage.created_at}


@dataclass(frozen=True, slots=True)
class GarageFilters:
    q: str | None = None
    garage_type: GarageType | None = None
    city: str | None = None
    sort: str | None = None


async def ensure_garage_usable(
    session: AsyncSession, user_id: uuid.UUID, garage_id: uuid.UUID | None
) -> None:
    """Validate a garage reference sent in a request body (must belong to the caller)."""
    if garage_id is None:
        return
    exists = await session.scalar(
        select(Garage.id).where(Garage.id == garage_id, Garage.user_id == user_id)
    )
    if exists is None:
        raise ValidationAppError(fields={"garage_id": "Unknown garage."})


class GarageService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_garages(
        self, user_id: uuid.UUID, filters: GarageFilters, params: PageParams
    ) -> Page[Garage]:
        stmt = select(Garage).where(Garage.user_id == user_id)
        if filters.garage_type:
            stmt = stmt.where(Garage.garage_type == filters.garage_type)
        if filters.city:
            stmt = stmt.where(Garage.city.ilike(like_pattern(filters.city), escape="\\"))
        if filters.q:
            pattern = like_pattern(filters.q)
            stmt = stmt.where(
                or_(
                    Garage.name.ilike(pattern, escape="\\"),
                    Garage.contact_name.ilike(pattern, escape="\\"),
                    Garage.city.ilike(pattern, escape="\\"),
                )
            )
        stmt = apply_sort(stmt, filters.sort, GARAGE_SORT_FIELDS, "name", Garage.id)
        return await paginate(self.session, stmt, params)

    async def get(self, user_id: uuid.UUID, garage_id: uuid.UUID) -> Garage:
        garage = await self.session.scalar(
            select(Garage).where(Garage.id == garage_id, Garage.user_id == user_id)
        )
        if garage is None:
            raise NotFoundError("Garage")
        return garage

    async def create(self, user_id: uuid.UUID, data: GarageCreate) -> Garage:
        garage = Garage(user_id=user_id, **data.model_dump())
        self.session.add(garage)
        await self.session.commit()
        return garage

    async def update(self, user_id: uuid.UUID, garage_id: uuid.UUID, data: GarageUpdate) -> Garage:
        garage = await self.get(user_id, garage_id)
        apply_updates(garage, data, required={"name", "garage_type"})
        await self.session.commit()
        return garage

    async def delete(self, user_id: uuid.UUID, garage_id: uuid.UUID) -> None:
        """Records that referenced the garage keep their history (garage_id set to NULL)."""
        result = await self.session.execute(
            delete(Garage).where(Garage.id == garage_id, Garage.user_id == user_id)
        )
        if result.rowcount == 0:  # type: ignore[attr-defined]
            raise NotFoundError("Garage")
        await self.session.commit()
