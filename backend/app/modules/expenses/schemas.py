"""Expense DTOs."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import Field, StringConstraints

from app.core.schemas import LongText, Mileage, Money, RequestModel, ResponseModel, ShortText
from app.modules.expenses.models import ExpenseCategory, ExpenseSource

Vendor = Annotated[str, StringConstraints(min_length=1, max_length=120)]


class ExpenseCreate(RequestModel):
    category: ExpenseCategory
    title: ShortText
    amount: Money
    expense_date: date
    mileage: Mileage | None = None
    vendor: Vendor | None = None
    notes: LongText | None = None


class ExpenseUpdate(RequestModel):
    category: ExpenseCategory | None = None
    title: ShortText | None = None
    amount: Money | None = None
    expense_date: date | None = None
    mileage: Mileage | None = None
    vendor: Vendor | None = None
    notes: LongText | None = None


class ExpenseResponse(ResponseModel):
    id: uuid.UUID
    vehicle_id: uuid.UUID
    category: ExpenseCategory
    title: str
    amount: Decimal
    currency: str = Field(description="Currency of the vehicle (ISO 4217).")
    expense_date: date
    mileage: int | None
    vendor: str | None
    source: ExpenseSource = Field(
        description="`manual`, or the record that maintains this expense (read-only then)."
    )
    source_id: uuid.UUID | None
    notes: str | None
    created_by_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
