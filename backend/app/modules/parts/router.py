"""Part replacement endpoints."""

import uuid
from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import ClockDep, DbSession
from app.api.openapi import VEHICLE_ERRORS
from app.core.pagination import PageDep, SearchQuery, paginated
from app.core.responses import ApiResponse, PaginatedResponse, success
from app.modules.parts.schemas import PartCreate, PartResponse, PartUpdate
from app.modules.parts.service import PartFilters, PartService, to_response
from app.modules.vehicles.access import VehicleContext, VehicleEditor, VehicleViewer

router = APIRouter(prefix="/vehicles/{vehicle_id}/parts", tags=["Parts"], responses=VEHICLE_ERRORS)


def get_part_service(session: DbSession, clock: ClockDep) -> PartService:
    return PartService(session, clock)


PartServiceDep = Annotated[PartService, Depends(get_part_service)]


def respond(service: PartService, ctx: VehicleContext, part: Any) -> dict[str, Any]:
    return success(to_response(part, ctx.vehicle.current_mileage, service.today(ctx)))


@router.get(
    "",
    response_model=PaginatedResponse[PartResponse],
    summary="Installed and replaced parts",
    description="Installed parts with an expected lifetime include their wear status.",
)
async def list_parts(
    ctx: VehicleViewer,
    service: PartServiceDep,
    page: PageDep,
    part_type_id: Annotated[uuid.UUID | None, Query()] = None,
    installed: Annotated[
        bool | None, Query(description="true: currently installed, false: removed")
    ] = None,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
    q: SearchQuery = None,
    sort: Annotated[
        str | None,
        Query(max_length=200, description="installed_date, installed_mileage, price, created_at"),
    ] = None,
) -> Any:
    filters = PartFilters(
        part_type_id=part_type_id,
        installed=installed,
        date_from=date_from,
        date_to=date_to,
        q=q,
        sort=sort,
    )
    return paginated(await service.list_parts(ctx, filters, page))


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[PartResponse],
    summary="Record an installed or replaced part",
    description=(
        "The installed part of the same type and position is marked as removed. Expected "
        "lifetimes default to the part type defaults."
    ),
)
async def create_part(body: PartCreate, ctx: VehicleEditor, service: PartServiceDep) -> Any:
    return respond(service, ctx, await service.create(ctx, body))


@router.get("/{part_id}", response_model=ApiResponse[PartResponse], summary="Get a part")
async def get_part(part_id: uuid.UUID, ctx: VehicleViewer, service: PartServiceDep) -> Any:
    return respond(service, ctx, await service.get(ctx, part_id))


@router.patch("/{part_id}", response_model=ApiResponse[PartResponse], summary="Update a part")
async def update_part(
    part_id: uuid.UUID, body: PartUpdate, ctx: VehicleEditor, service: PartServiceDep
) -> Any:
    return respond(service, ctx, await service.update(ctx, part_id, body))


@router.delete("/{part_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a part")
async def delete_part(part_id: uuid.UUID, ctx: VehicleEditor, service: PartServiceDep) -> None:
    await service.delete(ctx, part_id)
