"""Vehicle endpoints."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import ClockDep, CurrentUser, DbSession, RequestMetaDep, StorageDep
from app.api.openapi import VEHICLE_ERRORS, error_responses
from app.core.pagination import PageDep, SearchQuery, SortQuery, paginated
from app.core.responses import ApiResponse, PaginatedResponse, success
from app.modules.vehicles.access import VehicleEditor, VehicleOwner, VehicleViewer
from app.modules.vehicles.models import VehicleRole, VehicleStatus
from app.modules.vehicles.schemas import VehicleCreate, VehicleResponse, VehicleUpdate
from app.modules.vehicles.service import VehicleFilters, VehicleService, to_response

router = APIRouter(prefix="/vehicles", tags=["Vehicles"], responses=VEHICLE_ERRORS)


def get_vehicle_service(session: DbSession, clock: ClockDep) -> VehicleService:
    return VehicleService(session, clock)


VehicleServiceDep = Annotated[VehicleService, Depends(get_vehicle_service)]


@router.get(
    "",
    response_model=PaginatedResponse[VehicleResponse],
    summary="List my vehicles",
    description="Vehicles owned by the caller and vehicles shared with the caller.",
)
async def list_vehicles(
    user: CurrentUser,
    service: VehicleServiceDep,
    page: PageDep,
    status_: Annotated[VehicleStatus | None, Query(alias="status")] = None,
    role: Annotated[VehicleRole | None, Query(description="Filter by my role")] = None,
    q: SearchQuery = None,
    sort: SortQuery = None,
) -> Any:
    filters = VehicleFilters(status=status_, role=role, q=q, sort=sort)
    return paginated(await service.list_for_user(user, filters, page))


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[VehicleResponse],
    summary="Add a vehicle",
    responses=error_responses(409),
)
async def create_vehicle(body: VehicleCreate, user: CurrentUser, service: VehicleServiceDep) -> Any:
    vehicle = await service.create(user, body)
    return success(to_response(vehicle, VehicleRole.OWNER))


@router.get("/{vehicle_id}", response_model=ApiResponse[VehicleResponse], summary="Get a vehicle")
async def get_vehicle(ctx: VehicleViewer) -> Any:
    return success(to_response(ctx.vehicle, ctx.role))


@router.patch(
    "/{vehicle_id}",
    response_model=ApiResponse[VehicleResponse],
    summary="Update a vehicle",
    responses=error_responses(409),
)
async def update_vehicle(
    body: VehicleUpdate, ctx: VehicleEditor, service: VehicleServiceDep
) -> Any:
    vehicle = await service.update(ctx, body)
    return success(to_response(vehicle, ctx.role))


@router.delete(
    "/{vehicle_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a vehicle and its whole history",
    description="Owner only. Consider setting `status` to `sold` or `archived` instead.",
)
async def delete_vehicle(
    ctx: VehicleOwner, service: VehicleServiceDep, meta: RequestMetaDep, storage: StorageDep
) -> None:
    await service.delete(ctx, meta, storage)
