"""Chronological vehicle history built from every record table (one UNION ALL query).

Each source contributes rows with the same shape. Expenses linked to a maintenance record or
a part, and odometer readings derived from records, are skipped (the source record already
appears), so nothing is shown twice.
"""

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Any

import sqlalchemy as sa
from sqlalchemy import Select, func, literal, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import Page, PageParams
from app.modules.documents.models import VehicleDocument
from app.modules.expenses.models import Expense
from app.modules.fuel.models import FuelRecord
from app.modules.maintenance.models import MaintenanceKind, MaintenanceRecord, MaintenanceType
from app.modules.mileage.models import MileageEntry, MileageSource
from app.modules.parts.models import PartReplacement


class TimelineEventType(StrEnum):
    MILEAGE = "mileage"
    MAINTENANCE = "maintenance"
    REPAIR = "repair"
    PART = "part"
    EXPENSE = "expense"
    DOCUMENT = "document"
    FUEL = "fuel"


@dataclass(frozen=True, slots=True)
class TimelineEvent:
    type: TimelineEventType
    id: uuid.UUID
    date: date
    mileage: int | None
    title: str
    amount: Decimal | None
    subtype: str | None


EventSource = Callable[[uuid.UUID], Select[Any]]

# Readings recorded on their own; readings derived from a service, part or fill-up are
# already visible through that record.
STANDALONE_READINGS = (
    MileageSource.INITIAL,
    MileageSource.MANUAL,
    MileageSource.OBD,
    MileageSource.IMPORT,
)


def _row(
    event_type: Any,
    event_id: Any,
    event_date: Any,
    mileage: Any,
    title: Any,
    amount: Any,
    subtype: Any,
    created_at: Any,
) -> list[Any]:
    return [
        sa.cast(event_type, sa.String).label("type"),
        event_id.label("id"),
        event_date.label("date"),
        sa.cast(mileage, sa.Integer).label("mileage"),
        sa.cast(title, sa.String).label("title"),
        sa.cast(amount, sa.Numeric(12, 2)).label("amount"),
        sa.cast(subtype, sa.String).label("subtype"),
        created_at.label("created_at"),
    ]


def mileage_events(vehicle_id: uuid.UUID) -> Select[Any]:
    entry = MileageEntry
    return select(
        *_row(
            literal(TimelineEventType.MILEAGE.value),
            entry.id,
            entry.recorded_on,
            entry.mileage,
            func.concat(entry.mileage, " km"),
            sa.null(),
            entry.source,
            entry.created_at,
        )
    ).where(entry.vehicle_id == vehicle_id, entry.source.in_(STANDALONE_READINGS))


def maintenance_events(vehicle_id: uuid.UUID) -> Select[Any]:
    record = MaintenanceRecord
    event_type = sa.case(
        (record.kind == MaintenanceKind.REPAIR, TimelineEventType.REPAIR.value),
        else_=TimelineEventType.MAINTENANCE.value,
    )
    return (
        select(
            *_row(
                event_type,
                record.id,
                record.service_date,
                record.mileage,
                record.title,
                record.cost,
                MaintenanceType.code,
                record.created_at,
            )
        )
        .join(MaintenanceType, MaintenanceType.id == record.maintenance_type_id)
        .where(record.vehicle_id == vehicle_id)
    )


def part_events(vehicle_id: uuid.UUID) -> Select[Any]:
    part = PartReplacement
    total = sa.case(
        (sa.and_(part.price.is_(None), part.labor_cost.is_(None)), sa.null()),
        else_=func.coalesce(part.price, 0) + func.coalesce(part.labor_cost, 0),
    )
    return select(
        *_row(
            literal(TimelineEventType.PART.value),
            part.id,
            part.installed_date,
            part.installed_mileage,
            part.part_name,
            total,
            part.position,
            part.created_at,
        )
    ).where(part.vehicle_id == vehicle_id)


def expense_events(vehicle_id: uuid.UUID) -> Select[Any]:
    expense = Expense
    return select(
        *_row(
            literal(TimelineEventType.EXPENSE.value),
            expense.id,
            expense.expense_date,
            expense.mileage,
            expense.title,
            expense.amount,
            expense.category,
            expense.created_at,
        )
    ).where(
        expense.vehicle_id == vehicle_id,
        expense.maintenance_record_id.is_(None),
        expense.part_replacement_id.is_(None),
        expense.fuel_record_id.is_(None),
    )


def document_events(vehicle_id: uuid.UUID) -> Select[Any]:
    document = VehicleDocument
    return select(
        *_row(
            literal(TimelineEventType.DOCUMENT.value),
            document.id,
            document.issue_date,
            sa.null(),
            document.title,
            sa.null(),
            document.document_type,
            document.created_at,
        )
    ).where(document.vehicle_id == vehicle_id, document.issue_date.is_not(None))


def fuel_events(vehicle_id: uuid.UUID) -> Select[Any]:
    record = FuelRecord
    return select(
        *_row(
            literal(TimelineEventType.FUEL.value),
            record.id,
            record.fill_date,
            record.mileage,
            func.concat(func.round(record.liters, 2), " L"),
            record.total_price,
            record.fuel_type,
            record.created_at,
        )
    ).where(record.vehicle_id == vehicle_id)


EVENT_SOURCES: dict[TimelineEventType, EventSource] = {
    TimelineEventType.MILEAGE: mileage_events,
    TimelineEventType.MAINTENANCE: maintenance_events,
    TimelineEventType.REPAIR: maintenance_events,
    TimelineEventType.PART: part_events,
    TimelineEventType.EXPENSE: expense_events,
    TimelineEventType.DOCUMENT: document_events,
    TimelineEventType.FUEL: fuel_events,
}


@dataclass(frozen=True, slots=True)
class TimelineFilters:
    types: list[TimelineEventType] | None = None
    date_from: date | None = None
    date_to: date | None = None


class TimelineService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def events(
        self, vehicle_id: uuid.UUID, filters: TimelineFilters, params: PageParams
    ) -> Page[TimelineEvent]:
        wanted = set(filters.types or TimelineEventType)
        sources = {EVENT_SOURCES[event_type] for event_type in wanted}
        union = union_all(*(source(vehicle_id) for source in sources)).subquery("timeline")

        stmt = select(union).where(union.c.type.in_([t.value for t in wanted]))
        if filters.date_from:
            stmt = stmt.where(union.c.date >= filters.date_from)
        if filters.date_to:
            stmt = stmt.where(union.c.date <= filters.date_to)

        total = int(
            await self.session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        )
        rows = await self.session.execute(
            stmt.order_by(union.c.date.desc(), union.c.created_at.desc(), union.c.id.desc())
            .limit(params.limit)
            .offset(params.offset)
        )
        events = [
            TimelineEvent(
                type=TimelineEventType(row.type),
                id=row.id,
                date=row.date,
                mileage=row.mileage,
                title=row.title,
                amount=row.amount,
                subtype=row.subtype,
            )
            for row in rows
        ]
        return Page(events, total, params)
