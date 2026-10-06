"""Tire endpoints."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import ClockDep, DbSession
from app.api.openapi import VEHICLE_ERRORS, error_responses
from app.core.pagination import PageDep, paginated
from app.core.responses import ApiResponse, PaginatedResponse, success
from app.modules.tires.models import TireSeason, TireStatus
from app.modules.tires.schemas import (
    TireCreate,
    TireEventCreate,
    TireEventResponse,
    TireResponse,
    TireRotation,
    TireUpdate,
)
from app.modules.tires.service import TireService
from app.modules.vehicles.access import VehicleEditor, VehicleViewer

router = APIRouter(prefix="/vehicles/{vehicle_id}/tires", tags=["Tires"], responses=VEHICLE_ERRORS)


def get_tire_service(session: DbSession, clock: ClockDep) -> TireService:
    return TireService(session, clock)


TireServiceDep = Annotated[TireService, Depends(get_tire_service)]


@router.get("", response_model=ApiResponse[list[TireResponse]], summary="Tires of a vehicle")
async def list_tires(
    ctx: VehicleViewer,
    service: TireServiceDep,
    status_: Annotated[TireStatus | None, Query(alias="status")] = None,
    season: Annotated[TireSeason | None, Query()] = None,
) -> Any:
    return success(await service.list_tires(ctx, status_, season))


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[TireResponse],
    summary="Add a tire (mounted when a position is given, stored otherwise)",
    responses=error_responses(409),
)
async def create_tire(body: TireCreate, ctx: VehicleEditor, service: TireServiceDep) -> Any:
    return success(await service.create(ctx, body))


@router.post(
    "/rotations",
    response_model=ApiResponse[list[TireResponse]],
    summary="Rotate tires",
    description=(
        "Moves several mounted tires atomically and records a `rotated` event for each. "
        "Returns the mounted tires after the rotation."
    ),
)
async def rotate_tires(body: TireRotation, ctx: VehicleEditor, service: TireServiceDep) -> Any:
    return success(await service.rotate(ctx, body))


@router.get("/{tire_id}", response_model=ApiResponse[TireResponse], summary="Get a tire")
async def get_tire(tire_id: uuid.UUID, ctx: VehicleViewer, service: TireServiceDep) -> Any:
    return success(await service.get(ctx, tire_id))


@router.patch("/{tire_id}", response_model=ApiResponse[TireResponse], summary="Update a tire")
async def update_tire(
    tire_id: uuid.UUID, body: TireUpdate, ctx: VehicleEditor, service: TireServiceDep
) -> Any:
    return success(await service.update(ctx, tire_id, body))


@router.delete("/{tire_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a tire")
async def delete_tire(tire_id: uuid.UUID, ctx: VehicleEditor, service: TireServiceDep) -> None:
    await service.delete(ctx, tire_id)


@router.get(
    "/{tire_id}/events",
    response_model=PaginatedResponse[TireEventResponse],
    summary="History of a tire",
)
async def list_tire_events(
    tire_id: uuid.UUID, ctx: VehicleViewer, service: TireServiceDep, page: PageDep
) -> Any:
    return paginated(await service.list_events(ctx, tire_id, page))


@router.post(
    "/{tire_id}/events",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[TireEventResponse],
    summary="Record a tire event",
    description=(
        "`installed` mounts the tire at `to_position`, `removed` stores it, `discarded` "
        "retires it; `inspected` and `repaired` update tread depth and condition."
    ),
    responses=error_responses(409),
)
async def add_tire_event(
    tire_id: uuid.UUID, body: TireEventCreate, ctx: VehicleEditor, service: TireServiceDep
) -> Any:
    return success(await service.add_event(ctx, tire_id, body))
