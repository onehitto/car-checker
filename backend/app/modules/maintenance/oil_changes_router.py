"""Oil change endpoints."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, status

from app.api.deps import ClockDep, DbSession
from app.api.openapi import VEHICLE_ERRORS
from app.core.pagination import PageDep, paginated
from app.core.responses import ApiResponse, PaginatedResponse, success
from app.modules.maintenance.oil_changes import OilChangeService
from app.modules.maintenance.schemas import OilChangeCreate, OilChangeResponse, OilChangeUpdate
from app.modules.vehicles.access import VehicleEditor, VehicleViewer

router = APIRouter(
    prefix="/vehicles/{vehicle_id}/oil-changes", tags=["Oil changes"], responses=VEHICLE_ERRORS
)


def get_oil_change_service(session: DbSession, clock: ClockDep) -> OilChangeService:
    return OilChangeService(session, clock)


OilChangeServiceDep = Annotated[OilChangeService, Depends(get_oil_change_service)]


@router.get(
    "",
    response_model=PaginatedResponse[OilChangeResponse],
    summary="Oil change history",
)
async def list_oil_changes(ctx: VehicleViewer, service: OilChangeServiceDep, page: PageDep) -> Any:
    return paginated(await service.list_oil_changes(ctx, page))


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[OilChangeResponse],
    summary="Record an oil change",
    description=(
        "Creates an `oil_change` maintenance record with its oil details: the cost becomes a "
        "maintenance expense, the odometer and the oil change schedule move forward, and the "
        "oil filter schedule too when `oil_filter_changed` is true."
    ),
)
async def create_oil_change(
    body: OilChangeCreate, ctx: VehicleEditor, service: OilChangeServiceDep
) -> Any:
    return success(await service.create(ctx, body))


@router.get(
    "/{record_id}", response_model=ApiResponse[OilChangeResponse], summary="Get an oil change"
)
async def get_oil_change(
    record_id: uuid.UUID, ctx: VehicleViewer, service: OilChangeServiceDep
) -> Any:
    return success(await service.get(ctx, record_id))


@router.patch(
    "/{record_id}", response_model=ApiResponse[OilChangeResponse], summary="Update an oil change"
)
async def update_oil_change(
    record_id: uuid.UUID, body: OilChangeUpdate, ctx: VehicleEditor, service: OilChangeServiceDep
) -> Any:
    return success(await service.update(ctx, record_id, body))


@router.delete(
    "/{record_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete an oil change"
)
async def delete_oil_change(
    record_id: uuid.UUID, ctx: VehicleEditor, service: OilChangeServiceDep
) -> None:
    await service.delete(ctx, record_id)
