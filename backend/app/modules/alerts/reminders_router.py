"""Custom reminder endpoints."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import ClockDep, DbSession
from app.api.openapi import VEHICLE_ERRORS
from app.core.responses import ApiResponse, success
from app.modules.alerts.reminders import ReminderService
from app.modules.alerts.schemas import ReminderCreate, ReminderResponse, ReminderUpdate
from app.modules.vehicles.access import VehicleEditor, VehicleViewer

router = APIRouter(
    prefix="/vehicles/{vehicle_id}/reminders", tags=["Reminders"], responses=VEHICLE_ERRORS
)


def get_reminder_service(session: DbSession, clock: ClockDep) -> ReminderService:
    return ReminderService(session, clock)


ReminderServiceDep = Annotated[ReminderService, Depends(get_reminder_service)]


@router.get(
    "",
    response_model=ApiResponse[list[ReminderResponse]],
    summary="Custom reminders of a vehicle",
    description="Open reminders first (soonest due), then completed ones.",
)
async def list_reminders(
    ctx: VehicleViewer,
    service: ReminderServiceDep,
    completed: Annotated[bool | None, Query()] = None,
) -> Any:
    reminders = await service.list_reminders(ctx, completed)
    return success([service.to_response(ctx, reminder) for reminder in reminders])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[ReminderResponse],
    summary="Create a reminder (due at a date and/or a mileage)",
    description="An alert is raised when the reminder is due soon (warning windows).",
)
async def create_reminder(
    body: ReminderCreate, ctx: VehicleEditor, service: ReminderServiceDep
) -> Any:
    return success(service.to_response(ctx, await service.create(ctx, body)))


@router.get(
    "/{reminder_id}", response_model=ApiResponse[ReminderResponse], summary="Get a reminder"
)
async def get_reminder(
    reminder_id: uuid.UUID, ctx: VehicleViewer, service: ReminderServiceDep
) -> Any:
    return success(service.to_response(ctx, await service.get(ctx, reminder_id)))


@router.patch(
    "/{reminder_id}",
    response_model=ApiResponse[ReminderResponse],
    summary="Update, complete or reopen a reminder",
)
async def update_reminder(
    reminder_id: uuid.UUID, body: ReminderUpdate, ctx: VehicleEditor, service: ReminderServiceDep
) -> Any:
    return success(service.to_response(ctx, await service.update(ctx, reminder_id, body)))


@router.delete(
    "/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a reminder"
)
async def delete_reminder(
    reminder_id: uuid.UUID, ctx: VehicleEditor, service: ReminderServiceDep
) -> None:
    await service.delete(ctx, reminder_id)
