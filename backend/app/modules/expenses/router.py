"""Expense endpoints (per vehicle and across all accessible vehicles)."""

import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import ClockDep, CurrentUser, DbSession
from app.api.openapi import VEHICLE_ERRORS, error_responses
from app.core.pagination import PageDep, SearchQuery, paginated
from app.core.responses import ApiResponse, PaginatedResponse, success
from app.modules.expenses.models import Expense, ExpenseCategory, ExpenseSource
from app.modules.expenses.schemas import ExpenseCreate, ExpenseResponse, ExpenseUpdate
from app.modules.expenses.service import ExpenseFilters, ExpenseService
from app.modules.vehicles.access import VehicleEditor, VehicleViewer, accessible_vehicles_clause

router = APIRouter(tags=["Expenses"], responses=VEHICLE_ERRORS)

VEHICLE_PATH = "/vehicles/{vehicle_id}/expenses"


def get_expense_service(session: DbSession, clock: ClockDep) -> ExpenseService:
    return ExpenseService(session, clock)


ExpenseServiceDep = Annotated[ExpenseService, Depends(get_expense_service)]


@dataclass
class ExpenseQuery:
    category: Annotated[list[ExpenseCategory] | None, Query()] = None
    source: Annotated[ExpenseSource | None, Query()] = None
    date_from: Annotated[date | None, Query()] = None
    date_to: Annotated[date | None, Query()] = None
    amount_min: Annotated[Decimal | None, Query(ge=0)] = None
    amount_max: Annotated[Decimal | None, Query(ge=0)] = None
    q: SearchQuery = None
    sort: Annotated[
        str | None, Query(max_length=200, description="expense_date, amount, created_at")
    ] = None

    def filters(self) -> ExpenseFilters:
        return ExpenseFilters(**self.__dict__)


ExpenseQueryDep = Annotated[ExpenseQuery, Depends()]


@router.get(
    "/expenses",
    response_model=PaginatedResponse[ExpenseResponse],
    summary="Expenses of all my vehicles",
)
async def list_all_expenses(
    user: CurrentUser,
    service: ExpenseServiceDep,
    page: PageDep,
    query: ExpenseQueryDep,
    vehicle_id: Annotated[uuid.UUID | None, Query()] = None,
) -> Any:
    scope = accessible_vehicles_clause(Expense.vehicle_id, user.id, vehicle_id)
    return paginated(await service.list_expenses(scope, query.filters(), page))


@router.get(
    VEHICLE_PATH,
    response_model=PaginatedResponse[ExpenseResponse],
    summary="Expenses of a vehicle",
    description="Includes expenses maintained by maintenance records and part purchases.",
)
async def list_expenses(
    ctx: VehicleViewer, service: ExpenseServiceDep, page: PageDep, query: ExpenseQueryDep
) -> Any:
    scope = Expense.vehicle_id == ctx.vehicle_id
    return paginated(await service.list_expenses(scope, query.filters(), page))


@router.post(
    VEHICLE_PATH,
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[ExpenseResponse],
    summary="Add an expense",
)
async def create_expense(
    body: ExpenseCreate, ctx: VehicleEditor, service: ExpenseServiceDep
) -> Any:
    return success(await service.create(ctx, body))


@router.get(
    f"{VEHICLE_PATH}/{{expense_id}}",
    response_model=ApiResponse[ExpenseResponse],
    summary="Get an expense",
)
async def get_expense(expense_id: uuid.UUID, ctx: VehicleViewer, service: ExpenseServiceDep) -> Any:
    return success(await service.get(ctx.vehicle_id, expense_id))


@router.patch(
    f"{VEHICLE_PATH}/{{expense_id}}",
    response_model=ApiResponse[ExpenseResponse],
    summary="Update a manual expense",
    responses=error_responses(409),
)
async def update_expense(
    expense_id: uuid.UUID, body: ExpenseUpdate, ctx: VehicleEditor, service: ExpenseServiceDep
) -> Any:
    return success(await service.update(ctx, expense_id, body))


@router.delete(
    f"{VEHICLE_PATH}/{{expense_id}}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a manual expense",
    responses=error_responses(409),
)
async def delete_expense(
    expense_id: uuid.UUID, ctx: VehicleEditor, service: ExpenseServiceDep
) -> None:
    await service.delete(ctx, expense_id)
