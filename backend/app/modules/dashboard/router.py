"""Dashboard endpoints."""

from typing import Any

from fastapi import APIRouter

from app.api.deps import ClockDep, CurrentUser, DbSession
from app.api.openapi import VEHICLE_ERRORS
from app.core.responses import ApiResponse, success
from app.modules.dashboard.schemas import GlobalDashboard, VehicleDashboard
from app.modules.dashboard.service import DashboardService
from app.modules.vehicles.access import VehicleViewer

router = APIRouter(tags=["Dashboard"], responses=VEHICLE_ERRORS)


@router.get(
    "/vehicles/{vehicle_id}/dashboard",
    response_model=ApiResponse[VehicleDashboard],
    summary="Vehicle dashboard",
    description=(
        "Current mileage, health score, overdue and upcoming maintenance, expiring documents, "
        "worn parts, open alerts, recent maintenance and expenses, fuel and cost overview."
    ),
)
async def vehicle_dashboard(ctx: VehicleViewer, session: DbSession, clock: ClockDep) -> Any:
    return success(await DashboardService(session, clock).vehicle_dashboard(ctx))


@router.get(
    "/dashboard",
    response_model=ApiResponse[GlobalDashboard],
    summary="Dashboard of all my active vehicles",
)
async def global_dashboard(user: CurrentUser, session: DbSession, clock: ClockDep) -> Any:
    return success(await DashboardService(session, clock).global_dashboard(user))
