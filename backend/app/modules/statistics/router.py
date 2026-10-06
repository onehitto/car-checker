"""Statistics endpoints."""

import uuid
from dataclasses import dataclass
from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from app.api.deps import ClockDep, CurrentUser, DbSession
from app.api.openapi import VEHICLE_ERRORS
from app.core.responses import ApiResponse, success
from app.modules.expenses.models import Expense, ExpenseCategory
from app.modules.statistics.schemas import GlobalStatistics, VehicleStatistics
from app.modules.statistics.service import StatisticsQuery, StatisticsService
from app.modules.vehicles.access import VehicleViewer, accessible_vehicles_clause

router = APIRouter(tags=["Statistics"], responses=VEHICLE_ERRORS)


@dataclass
class StatisticsParams:
    date_from: Annotated[date | None, Query()] = None
    date_to: Annotated[date | None, Query()] = None
    year: Annotated[int | None, Query(ge=1900, le=2100, description="Calendar year")] = None
    category: Annotated[list[ExpenseCategory] | None, Query()] = None

    def query(self) -> StatisticsQuery:
        return StatisticsQuery(
            date_from=self.date_from,
            date_to=self.date_to,
            year=self.year,
            categories=self.category,
        )


StatisticsParamsDep = Annotated[StatisticsParams, Depends()]


@router.get(
    "/vehicles/{vehicle_id}/statistics",
    response_model=ApiResponse[VehicleStatistics],
    summary="Cost and usage statistics of a vehicle",
    description=(
        "Totals by category, month and year, average monthly cost, cost per km, maintenance "
        "frequency, most expensive repairs and fuel summary. Without a period, statistics "
        "cover the first expense up to today."
    ),
)
async def vehicle_statistics(
    ctx: VehicleViewer, session: DbSession, clock: ClockDep, params: StatisticsParamsDep
) -> Any:
    today = clock.today(ctx.user.timezone)
    stats = await StatisticsService(session).vehicle_statistics(ctx.vehicle, params.query(), today)
    return success(stats)


@router.get(
    "/statistics",
    response_model=ApiResponse[GlobalStatistics],
    summary="Cost statistics across my vehicles",
    description="Grouped by currency: amounts in different currencies are never summed.",
)
async def global_statistics(
    user: CurrentUser,
    session: DbSession,
    clock: ClockDep,
    params: StatisticsParamsDep,
    vehicle_id: Annotated[uuid.UUID | None, Query()] = None,
) -> Any:
    scope = accessible_vehicles_clause(Expense.vehicle_id, user.id, vehicle_id)
    today = clock.today(user.timezone)
    return success(await StatisticsService(session).global_statistics(scope, params.query(), today))
