"""Alert endpoints."""

import uuid
from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from app.api.deps import ClockDep, CurrentUser, DbSession
from app.api.openapi import AUTHENTICATED_ERRORS, VEHICLE_ERRORS, error_responses
from app.core.pagination import PageDep, paginated
from app.core.responses import ApiResponse, PaginatedResponse, success
from app.modules.alerts.models import AlertPriority, AlertStatus, AlertType
from app.modules.alerts.schemas import AlertResponse, AlertSummary, AlertUpdate, ReadAllResponse
from app.modules.alerts.service import AlertFilters, AlertService
from app.modules.vehicles.access import VehicleViewer

router = APIRouter(tags=["Alerts"], responses=AUTHENTICATED_ERRORS)


def get_alert_service(session: DbSession, clock: ClockDep) -> AlertService:
    return AlertService(session, clock)


AlertServiceDep = Annotated[AlertService, Depends(get_alert_service)]


@dataclass
class AlertQuery:
    status: Annotated[list[AlertStatus] | None, Query()] = None
    priority: Annotated[list[AlertPriority] | None, Query()] = None
    alert_type: Annotated[list[AlertType] | None, Query()] = None
    sort: Annotated[
        str | None, Query(max_length=200, description="created_at, priority, trigger_date")
    ] = None


AlertQueryDep = Annotated[AlertQuery, Depends()]


@router.get(
    "/alerts",
    response_model=PaginatedResponse[AlertResponse],
    summary="My alerts",
    description="Newest first by default; `sort=-priority` shows the most critical first.",
)
async def list_alerts(
    user: CurrentUser,
    service: AlertServiceDep,
    page: PageDep,
    query: AlertQueryDep,
    vehicle_id: Annotated[uuid.UUID | None, Query()] = None,
) -> Any:
    filters = AlertFilters(vehicle_id=vehicle_id, **query.__dict__)
    return paginated(await service.list_alerts(user.id, filters, page))


@router.get(
    "/alerts/summary",
    response_model=ApiResponse[AlertSummary],
    summary="Counts of my open alerts",
)
async def alert_summary(
    user: CurrentUser,
    service: AlertServiceDep,
    vehicle_id: Annotated[uuid.UUID | None, Query()] = None,
) -> Any:
    return success(await service.summary(user.id, vehicle_id))


@router.post(
    "/alerts/read-all",
    response_model=ApiResponse[ReadAllResponse],
    summary="Mark all my active alerts as read",
)
async def read_all(
    user: CurrentUser,
    service: AlertServiceDep,
    vehicle_id: Annotated[uuid.UUID | None, Query()] = None,
) -> Any:
    return success({"updated": await service.mark_all_read(user.id, vehicle_id)})


@router.get(
    "/alerts/{alert_id}",
    response_model=ApiResponse[AlertResponse],
    summary="Get an alert",
    responses=error_responses(404),
)
async def get_alert(alert_id: uuid.UUID, user: CurrentUser, service: AlertServiceDep) -> Any:
    return success(await service.get(user.id, alert_id))


@router.patch(
    "/alerts/{alert_id}",
    response_model=ApiResponse[AlertResponse],
    summary="Mark an alert read, unread, dismissed or resolved",
    responses=error_responses(404),
)
async def update_alert(
    alert_id: uuid.UUID, body: AlertUpdate, user: CurrentUser, service: AlertServiceDep
) -> Any:
    return success(await service.set_status(user.id, alert_id, body.status))


@router.get(
    "/vehicles/{vehicle_id}/alerts",
    response_model=PaginatedResponse[AlertResponse],
    summary="My alerts for a vehicle",
    responses=VEHICLE_ERRORS,
)
async def list_vehicle_alerts(
    ctx: VehicleViewer, service: AlertServiceDep, page: PageDep, query: AlertQueryDep
) -> Any:
    filters = AlertFilters(vehicle_id=ctx.vehicle_id, **query.__dict__)
    return paginated(await service.list_alerts(ctx.user.id, filters, page))
