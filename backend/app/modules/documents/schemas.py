"""Document DTOs."""

import uuid
from datetime import date, datetime
from typing import Annotated, Self

from pydantic import AfterValidator, Field, StringConstraints, model_validator

from app.core.schemas import LongText, RequestModel, ResponseModel
from app.modules.documents.expiration import (
    DEFAULT_REMINDER_DAYS,
    DocumentStatus,
    normalize_reminder_days,
)
from app.modules.documents.models import DocumentType

ReminderDays = Annotated[
    list[int],
    AfterValidator(normalize_reminder_days),
    Field(
        description="Days before expiration at which reminders are sent.",
        examples=[[90, 30, 15, 7, 1, 0]],
    ),
]
Text80 = Annotated[str, StringConstraints(min_length=1, max_length=80)]


class DocumentFields(RequestModel):
    document_number: Text80 | None = None
    issue_date: date | None = None
    expiration_date: date | None = None
    provider: Annotated[str, StringConstraints(min_length=1, max_length=120)] | None = None
    notes: LongText | None = None

    @model_validator(mode="after")
    def _expiration_after_issue(self) -> Self:
        if self.issue_date and self.expiration_date and self.expiration_date < self.issue_date:
            raise ValueError("expiration_date cannot be before issue_date.")
        return self


class DocumentCreate(DocumentFields):
    document_type: DocumentType
    title: Annotated[str, StringConstraints(min_length=1, max_length=150)]
    reminder_days: ReminderDays = Field(default_factory=lambda: list(DEFAULT_REMINDER_DAYS))


class DocumentUpdate(DocumentFields):
    document_type: DocumentType | None = None
    title: Annotated[str, StringConstraints(min_length=1, max_length=150)] | None = None
    reminder_days: ReminderDays | None = None


class DocumentResponse(ResponseModel):
    id: uuid.UUID
    vehicle_id: uuid.UUID
    document_type: DocumentType
    title: str
    document_number: str | None
    issue_date: date | None
    expiration_date: date | None
    provider: str | None
    reminder_days: list[int]
    notes: str | None
    status: DocumentStatus = DocumentStatus.VALID
    days_until_expiration: int | None = None
    created_by_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
