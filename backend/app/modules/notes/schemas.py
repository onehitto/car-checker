"""Note DTOs."""

import uuid
from datetime import datetime
from typing import Annotated, Self

from pydantic import Field, StringConstraints, model_validator

from app.core.schemas import RequestModel, ResponseModel, ShortText
from app.modules.notes.models import NoteCategory, NoteEntity

NoteBody = Annotated[str, StringConstraints(min_length=1, max_length=10_000)]


class NoteCreate(RequestModel):
    body: NoteBody
    title: ShortText | None = None
    category: NoteCategory = NoteCategory.GENERAL
    entity_type: NoteEntity | None = Field(
        default=None, description="Record of this vehicle the note is about (none: the vehicle)."
    )
    entity_id: uuid.UUID | None = None
    is_pinned: bool = False

    @model_validator(mode="after")
    def _entity_pair(self) -> Self:
        if (self.entity_type is None) != (self.entity_id is None):
            raise ValueError("entity_type and entity_id go together.")
        return self


class NoteUpdate(RequestModel):
    body: NoteBody | None = None
    title: ShortText | None = None
    category: NoteCategory | None = None
    is_pinned: bool | None = None


class NoteResponse(ResponseModel):
    id: uuid.UUID
    vehicle_id: uuid.UUID
    user_id: uuid.UUID | None = Field(description="Author.")
    entity_type: NoteEntity | None
    entity_id: uuid.UUID | None
    category: NoteCategory
    title: str | None
    body: str
    is_pinned: bool
    created_at: datetime
    updated_at: datetime
