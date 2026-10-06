"""Maintenance schedule endpoints."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import ClockDep, DbSession
from app.api.openapi import VEHICLE_ERRORS, error_responses
from app.core.responses import ApiResponse, success
from app.modules.maintenance.calculator import DueStatus
from app.modules.maintenance.schedules import ScheduleService
from app.modules.maintenance.schemas import ScheduleCreate, ScheduleResponse, ScheduleUpdate
from app.modules.vehicles.access import VehicleEditor, VehicleViewer

router = APIRouter(
    prefix="/vehicles/{vehicle_id}/maintenance-schedules",
    tags=["Maintenance schedules"],
    responses=VEHICLE_ERRORS,
)


def get_schedule_service(session: DbSession, clock: ClockDep) -> ScheduleService:
    return ScheduleService(session, clock)


ScheduleServiceDep = Annotated[ScheduleService, Depends(get_schedule_service)]


@router.get(
    "",
    response_model=ApiResponse[list[ScheduleResponse]],
    summary="Maintenance schedules with their current status",
    description=(
        "Most urgent first. Status: `overdue`, `due`, `due_soon`, `upcoming`, `ok` or "
        "`unknown`, computed from the current odometer and today's date."
    ),
)
async def list_schedules(
    ctx: VehicleViewer,
    service: ScheduleServiceDep,
    status_: Annotated[list[DueStatus] | None, Query(alias="status")] = None,
) -> Any:
    views = await service.list_views(ctx, set(status_) if status_ else None)
    return success([view.to_response() for view in views])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[ScheduleResponse],
    summary="Create a maintenance schedule",
    responses=error_responses(409),
)
async def create_schedule(
    body: ScheduleCreate, ctx: VehicleEditor, service: ScheduleServiceDep
) -> Any:
    return success((await service.create(ctx, body)).to_response())


@router.get(
    "/{schedule_id}",
    response_model=ApiResponse[ScheduleResponse],
    summary="Get a maintenance schedule",
)
async def get_schedule(
    schedule_id: uuid.UUID, ctx: VehicleViewer, service: ScheduleServiceDep
) -> Any:
    return success((await service.get_view(ctx, schedule_id)).to_response())


@router.patch(
    "/{schedule_id}",
    response_model=ApiResponse[ScheduleResponse],
    summary="Update a maintenance schedule",
)
async def update_schedule(
    schedule_id: uuid.UUID, body: ScheduleUpdate, ctx: VehicleEditor, service: ScheduleServiceDep
) -> Any:
    return success((await service.update(ctx, schedule_id, body)).to_response())


@router.delete(
    "/{schedule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a maintenance schedule",
)
async def delete_schedule(
    schedule_id: uuid.UUID, ctx: VehicleEditor, service: ScheduleServiceDep
) -> None:
    await service.delete(ctx, schedule_id)
