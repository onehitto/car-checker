"""Vehicle document use cases."""

import uuid
from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlalchemy import ColumnElement, and_, delete, func, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock
from app.core.exceptions import NotFoundError, ValidationAppError
from app.core.pagination import Page, PageParams, apply_sort, like_pattern, paginate
from app.core.updates import apply_updates
from app.modules.documents.expiration import (
    DEFAULT_EXPIRING_SOON_DAYS,
    DocumentStatus,
    document_state,
)
from app.modules.documents.models import DocumentType, VehicleDocument
from app.modules.documents.schemas import DocumentCreate, DocumentResponse, DocumentUpdate
from app.modules.vehicles.access import VehicleContext

DOCUMENT_SORT_FIELDS = {
    "expiration_date": VehicleDocument.expiration_date,
    "issue_date": VehicleDocument.issue_date,
    "title": VehicleDocument.title,
    "created_at": VehicleDocument.created_at,
}
REQUIRED_FIELDS = frozenset({"document_type", "title", "reminder_days"})


@dataclass(frozen=True, slots=True)
class DocumentFilters:
    document_type: DocumentType | None = None
    status: DocumentStatus | None = None
    expires_before: date | None = None
    q: str | None = None
    sort: str | None = None


def to_response(document: VehicleDocument, today: date) -> DocumentResponse:
    state = document_state(document.expiration_date, document.reminder_days, today)
    return DocumentResponse.model_validate(document).model_copy(
        update={"status": state.status, "days_until_expiration": state.days_until_expiration}
    )


def status_clause(status: DocumentStatus, today: date) -> ColumnElement[bool]:
    """SQL equivalent of `document_state(...).status` (reminder_days is stored largest first)."""
    doc = VehicleDocument
    window_end = literal(today) + func.coalesce(doc.reminder_days[1], DEFAULT_EXPIRING_SOON_DAYS)
    if status is DocumentStatus.EXPIRED:
        return doc.expiration_date < today
    if status is DocumentStatus.EXPIRING_SOON:
        return and_(doc.expiration_date >= today, doc.expiration_date <= window_end)
    return or_(doc.expiration_date.is_(None), doc.expiration_date > window_end)


class DocumentService:
    def __init__(self, session: AsyncSession, clock: Clock) -> None:
        self.session = session
        self.clock = clock

    async def list_documents(
        self,
        scope: ColumnElement[bool],
        filters: DocumentFilters,
        params: PageParams,
        today: date,
    ) -> Page[DocumentResponse]:
        stmt = select(VehicleDocument).where(scope)
        if filters.document_type:
            stmt = stmt.where(VehicleDocument.document_type == filters.document_type)
        if filters.status:
            stmt = stmt.where(status_clause(filters.status, today))
        if filters.expires_before:
            stmt = stmt.where(VehicleDocument.expiration_date <= filters.expires_before)
        if filters.q:
            pattern = like_pattern(filters.q)
            stmt = stmt.where(
                or_(
                    VehicleDocument.title.ilike(pattern, escape="\\"),
                    VehicleDocument.provider.ilike(pattern, escape="\\"),
                    VehicleDocument.document_number.ilike(pattern, escape="\\"),
                )
            )
        stmt = apply_sort(
            stmt, filters.sort, DOCUMENT_SORT_FIELDS, "expiration_date", VehicleDocument.id
        )
        page = await paginate(self.session, stmt, params)
        return page.map(lambda document: to_response(document, today))

    async def get(self, vehicle_id: uuid.UUID, document_id: uuid.UUID) -> VehicleDocument:
        document = await self.session.scalar(
            select(VehicleDocument).where(
                VehicleDocument.id == document_id, VehicleDocument.vehicle_id == vehicle_id
            )
        )
        if document is None:
            raise NotFoundError("Document")
        return document

    async def create(self, ctx: VehicleContext, data: DocumentCreate) -> VehicleDocument:
        document = VehicleDocument(
            **data.model_dump(), vehicle_id=ctx.vehicle_id, created_by_id=ctx.user.id
        )
        self.session.add(document)
        await self.session.commit()
        return document

    async def update(
        self, ctx: VehicleContext, document_id: uuid.UUID, data: DocumentUpdate
    ) -> VehicleDocument:
        document = await self.get(ctx.vehicle_id, document_id)
        apply_updates(document, data, required=REQUIRED_FIELDS)
        self._check_dates(document)
        await self.session.commit()
        return document

    async def delete(self, ctx: VehicleContext, document_id: uuid.UUID) -> None:
        result = await self.session.execute(
            delete(VehicleDocument).where(
                VehicleDocument.id == document_id, VehicleDocument.vehicle_id == ctx.vehicle_id
            )
        )
        if result.rowcount == 0:  # type: ignore[attr-defined]
            raise NotFoundError("Document")
        await self.session.commit()

    @staticmethod
    def _check_dates(document: Any) -> None:
        if (
            document.issue_date
            and document.expiration_date
            and document.expiration_date < document.issue_date
        ):
            raise ValidationAppError(fields={"expiration_date": "Cannot be before issue_date."})
