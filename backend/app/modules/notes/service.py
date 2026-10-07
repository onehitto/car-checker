"""Note use cases."""

import uuid
from dataclasses import dataclass

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.pagination import Page, PageParams, like_pattern, paginate
from app.core.updates import apply_updates
from app.modules.attachments.service import ensure_vehicle_record
from app.modules.notes.models import Note, NoteCategory, NoteEntity
from app.modules.notes.schemas import NoteCreate, NoteUpdate
from app.modules.vehicles.access import VehicleContext


@dataclass(frozen=True, slots=True)
class NoteFilters:
    category: NoteCategory | None = None
    entity_type: NoteEntity | None = None
    entity_id: uuid.UUID | None = None
    pinned: bool | None = None
    q: str | None = None


class NoteService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_notes(
        self, ctx: VehicleContext, filters: NoteFilters, params: PageParams
    ) -> Page[Note]:
        stmt = select(Note).where(Note.vehicle_id == ctx.vehicle_id)
        if filters.category:
            stmt = stmt.where(Note.category == filters.category)
        if filters.entity_type:
            stmt = stmt.where(Note.entity_type == filters.entity_type)
        if filters.entity_id:
            stmt = stmt.where(Note.entity_id == filters.entity_id)
        if filters.pinned is not None:
            stmt = stmt.where(Note.is_pinned.is_(filters.pinned))
        if filters.q:
            pattern = like_pattern(filters.q)
            stmt = stmt.where(
                or_(Note.title.ilike(pattern, escape="\\"), Note.body.ilike(pattern, escape="\\"))
            )
        # Pinned notes first, then the most recent.
        stmt = stmt.order_by(Note.is_pinned.desc(), Note.created_at.desc(), Note.id.desc())
        return await paginate(self.session, stmt, params)

    async def get(self, ctx: VehicleContext, note_id: uuid.UUID) -> Note:
        note = await self.session.scalar(
            select(Note).where(Note.id == note_id, Note.vehicle_id == ctx.vehicle_id)
        )
        if note is None:
            raise NotFoundError("Note")
        return note

    async def create(self, ctx: VehicleContext, data: NoteCreate) -> Note:
        if data.entity_type and data.entity_id:
            await ensure_vehicle_record(
                self.session, ctx.vehicle_id, data.entity_type.value, data.entity_id
            )
        note = Note(**data.model_dump(), vehicle_id=ctx.vehicle_id, user_id=ctx.user.id)
        self.session.add(note)
        await self.session.commit()
        return note

    async def update(self, ctx: VehicleContext, note_id: uuid.UUID, data: NoteUpdate) -> Note:
        note = await self.get(ctx, note_id)
        apply_updates(note, data, required={"body", "category", "is_pinned"})
        await self.session.commit()
        return note

    async def delete(self, ctx: VehicleContext, note_id: uuid.UUID) -> None:
        result = await self.session.execute(
            delete(Note).where(Note.id == note_id, Note.vehicle_id == ctx.vehicle_id)
        )
        if result.rowcount == 0:  # type: ignore[attr-defined]
            raise NotFoundError("Note")
        await self.session.commit()
