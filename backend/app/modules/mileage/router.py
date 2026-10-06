"""Mileage history endpoints."""

import uuid
from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import ClockDep, DbSession, RequestMetaDep
from app.api.openapi import VEHICLE_ERRORS
from app.core.pagination import PageDep, paginated
from app.core.responses import ApiResponse, PaginatedResponse, success
from app.modules.mileage.models import MileageSource
from app.modules.mileage.schemas import MileageCreate, MileageEntryResponse, MileageUpdateResponse
from app.modules.mileage.service import MileageFilters, MileageService
from app.modules.vehicles.access import VehicleEditor, VehicleViewer

router = APIRouter(
    prefix="/vehicles/{vehicle_id}/mileage", tags=["Mileage"], responses=VEHICLE_ERRORS
)


def get_mileage_service(session: DbSession, clock: ClockDep) -> MileageService:
    return MileageService(session, clock)


MileageServiceDep = Annotated[MileageService, Depends(get_mileage_service)]


@router.get(
    "",
    response_model=PaginatedResponse[MileageEntryResponse],
    summary="Mileage history",
    description="Readings ordered from the most recent.",
)
async def list_mileage(
    ctx: VehicleViewer,
    service: MileageServiceDep,
    page: PageDep,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
    source: Annotated[MileageSource | None, Query()] = None,
) -> Any:
    filters = MileageFilters(date_from=date_from, date_to=date_to, source=source)
    return paginated(await service.list_entries(ctx.vehicle_id, filters, page))


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[MileageUpdateResponse],
    summary="Record an odometer reading",
    description=(
        "Updates the vehicle's current mileage when the reading is the most recent one. "
        "A reading lower than a previous one is refused with `MILEAGE_DECREASE` unless "
        "`force` is true."
    ),
)
async def add_mileage(
    body: MileageCreate, ctx: VehicleEditor, service: MileageServiceDep, meta: RequestMetaDep
) -> Any:
    entry = await service.add_reading(ctx, body, meta)
    return success({"current_mileage": ctx.vehicle.current_mileage, "entry": entry})


@router.delete(
    "/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a reading",
    description="The current mileage is recomputed from the remaining history.",
)
async def delete_mileage(
    entry_id: uuid.UUID, ctx: VehicleEditor, service: MileageServiceDep
) -> None:
    await service.delete_reading(ctx, entry_id)
