"""Expense use cases and the linked-expense ledger.

Records that cost money (maintenance records, standalone part purchases, fuel fill-ups) own
exactly one linked expense, created/updated/removed in the same transaction. Statistics then
read a single table and nothing is counted twice.
"""

import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import ColumnElement, and_, delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock
from app.core.exceptions import ConflictError, NotFoundError
from app.core.pagination import Page, PageParams, apply_sort, like_pattern, paginate
from app.core.schemas import ensure_not_future
from app.core.updates import apply_updates
from app.modules.expenses.models import Expense, ExpenseCategory, ExpenseSource
from app.modules.expenses.schemas import ExpenseCreate, ExpenseUpdate
from app.modules.maintenance.models import MaintenanceKind, MaintenanceRecord
from app.modules.parts.models import PartReplacement
from app.modules.vehicles.access import VehicleContext

EXPENSE_SORT_FIELDS = {
    "expense_date": Expense.expense_date,
    "amount": Expense.amount,
    "created_at": Expense.created_at,
}
REQUIRED_FIELDS = frozenset({"category", "title", "amount", "expense_date"})


@dataclass(frozen=True, slots=True)
class ExpenseFilters:
    category: list[ExpenseCategory] | None = None
    source: ExpenseSource | None = None
    date_from: date | None = None
    date_to: date | None = None
    amount_min: Decimal | None = None
    amount_max: Decimal | None = None
    q: str | None = None
    sort: str | None = None


def source_clause(source: ExpenseSource) -> ColumnElement[bool]:
    if source is ExpenseSource.MAINTENANCE:
        return Expense.maintenance_record_id.is_not(None)
    if source is ExpenseSource.PART:
        return Expense.part_replacement_id.is_not(None)
    return and_(Expense.maintenance_record_id.is_(None), Expense.part_replacement_id.is_(None))


class ExpenseLedger:
    """Keeps linked expenses in sync with their source records (no commit)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _upsert(
        self, link: dict[str, uuid.UUID], amount: Decimal | None, **values: Any
    ) -> None:
        column, source_id = next(iter(link.items()))
        expense = await self.session.scalar(
            select(Expense).where(getattr(Expense, column) == source_id)
        )
        if amount is None or amount <= 0:
            if expense is not None:
                await self.session.delete(expense)
            return
        if expense is None:
            expense = Expense(**link)
            self.session.add(expense)
        expense.amount = amount
        for name, value in values.items():
            setattr(expense, name, value)

    async def sync_maintenance(self, record: MaintenanceRecord) -> None:
        category = (
            ExpenseCategory.REPAIRS
            if record.kind is MaintenanceKind.REPAIR
            else ExpenseCategory.MAINTENANCE
        )
        await self._upsert(
            {"maintenance_record_id": record.id},
            record.cost,
            vehicle_id=record.vehicle_id,
            category=category,
            title=record.title,
            expense_date=record.service_date,
            mileage=record.mileage,
            created_by_id=record.created_by_id,
        )

    async def sync_part(self, part: PartReplacement) -> None:
        # Parts installed during a maintenance are already costed by that maintenance.
        amount = None if part.maintenance_record_id else part.total_cost
        await self._upsert(
            {"part_replacement_id": part.id},
            amount,
            vehicle_id=part.vehicle_id,
            category=ExpenseCategory.PARTS,
            title=part.part_name,
            expense_date=part.installed_date,
            mileage=part.installed_mileage,
            vendor=part.brand,
            created_by_id=part.created_by_id,
        )


class ExpenseService:
    def __init__(self, session: AsyncSession, clock: Clock) -> None:
        self.session = session
        self.clock = clock

    async def list_expenses(
        self, scope: ColumnElement[bool], filters: ExpenseFilters, params: PageParams
    ) -> Page[Expense]:
        stmt = select(Expense).where(scope)
        if filters.category:
            stmt = stmt.where(Expense.category.in_(filters.category))
        if filters.source:
            stmt = stmt.where(source_clause(filters.source))
        if filters.date_from:
            stmt = stmt.where(Expense.expense_date >= filters.date_from)
        if filters.date_to:
            stmt = stmt.where(Expense.expense_date <= filters.date_to)
        if filters.amount_min is not None:
            stmt = stmt.where(Expense.amount >= filters.amount_min)
        if filters.amount_max is not None:
            stmt = stmt.where(Expense.amount <= filters.amount_max)
        if filters.q:
            pattern = like_pattern(filters.q)
            stmt = stmt.where(
                or_(
                    Expense.title.ilike(pattern, escape="\\"),
                    Expense.vendor.ilike(pattern, escape="\\"),
                    Expense.notes.ilike(pattern, escape="\\"),
                )
            )
        stmt = apply_sort(stmt, filters.sort, EXPENSE_SORT_FIELDS, "-expense_date", Expense.id)
        return await paginate(self.session, stmt, params)

    async def get(self, vehicle_id: uuid.UUID, expense_id: uuid.UUID) -> Expense:
        expense = await self.session.scalar(
            select(Expense)
            .where(Expense.id == expense_id, Expense.vehicle_id == vehicle_id)
            .execution_options(populate_existing=True)
        )
        if expense is None:
            raise NotFoundError("Expense")
        return expense

    async def create(self, ctx: VehicleContext, data: ExpenseCreate) -> Expense:
        ensure_not_future(data.expense_date, self.clock.today(ctx.user.timezone), "expense_date")
        expense = Expense(**data.model_dump(), vehicle_id=ctx.vehicle_id, created_by_id=ctx.user.id)
        self.session.add(expense)
        await self.session.commit()
        return await self.get(ctx.vehicle_id, expense.id)

    async def update(
        self, ctx: VehicleContext, expense_id: uuid.UUID, data: ExpenseUpdate
    ) -> Expense:
        expense = await self._get_manual(ctx.vehicle_id, expense_id)
        changes = data.model_dump(exclude_unset=True)
        ensure_not_future(
            changes.get("expense_date"), self.clock.today(ctx.user.timezone), "expense_date"
        )
        apply_updates(expense, data, required=REQUIRED_FIELDS)
        await self.session.commit()
        return await self.get(ctx.vehicle_id, expense.id)

    async def delete(self, ctx: VehicleContext, expense_id: uuid.UUID) -> None:
        expense = await self._get_manual(ctx.vehicle_id, expense_id)
        await self.session.execute(delete(Expense).where(Expense.id == expense.id))
        await self.session.commit()

    async def _get_manual(self, vehicle_id: uuid.UUID, expense_id: uuid.UUID) -> Expense:
        expense = await self.get(vehicle_id, expense_id)
        if expense.source is not ExpenseSource.MANUAL:
            raise ConflictError(
                f"This expense is maintained by its {expense.source.value} record; "
                "edit that record instead.",
                code="EXPENSE_LINKED_TO_SOURCE",
            )
        return expense
