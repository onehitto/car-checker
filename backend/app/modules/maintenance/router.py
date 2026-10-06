"""Maintenance record endpoints (per vehicle and across all accessible vehicles)."""

import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import ClockDep, CurrentUser, DbSession
from app.api.openapi import VEHICLE_ERRORS
from app.core.pagination import PageDep, SearchQuery, paginated
from app.core.responses import ApiResponse, PaginatedResponse, success
from app.modules.maintenance.models import MaintenanceKind, MaintenanceRecord
from app.modules.maintenance.records import MaintenanceFilters, MaintenanceRecordService
from app.modules.maintenance.schemas import (
    MaintenanceRecordCreate,
    MaintenanceRecordResponse,
    MaintenanceRecordUpdate,
)
from app.modules.vehicles.access import VehicleEditor, VehicleViewer, accessible_vehicles_clause

router = APIRouter(tags=["Maintenance"], responses=VEHICLE_ERRORS)

VEHICLE_PATH = "/vehicles/{vehicle_id}/maintenance"


def get_record_service(session: DbSession, clock: ClockDep) -> MaintenanceRecordService:
    return MaintenanceRecordService(session, clock)


RecordServiceDep = Annotated[MaintenanceRecordService, Depends(get_record_service)]


@dataclass
class MaintenanceQuery:
    """Filters shared by the per-vehicle and the global list endpoints."""

    maintenance_type_id: Annotated[uuid.UUID | None, Query()] = None
    kind: Annotated[MaintenanceKind | None, Query()] = None
    garage_id: Annotated[uuid.UUID | None, Query()] = None
    date_from: Annotated[date | None, Query()] = None
    date_to: Annotated[date | None, Query()] = None
    mileage_min: Annotated[int | None, Query(ge=0)] = None
    mileage_max: Annotated[int | None, Query(ge=0)] = None
    cost_min: Annotated[Decimal | None, Query(ge=0)] = None
    cost_max: Annotated[Decimal | None, Query(ge=0)] = None
    q: SearchQuery = None
    sort: Annotated[
        str | None,
        Query(
            max_length=200,
            description="service_date, mileage, cost, created_at; prefix '-' for descending.",
        ),
    ] = None

    def filters(self) -> MaintenanceFilters:
        return MaintenanceFilters(**self.__dict__)


MaintenanceQueryDep = Annotated[MaintenanceQuery, Depends()]


@router.get(
    "/maintenance",
    response_model=PaginatedResponse[MaintenanceRecordResponse],
    summary="Maintenance records of all my vehicles",
)
async def list_all_records(
    user: CurrentUser,
    service: RecordServiceDep,
    page: PageDep,
    query: MaintenanceQueryDep,
    vehicle_id: Annotated[uuid.UUID | None, Query()] = None,
) -> Any:
    scope = accessible_vehicles_clause(MaintenanceRecord.vehicle_id, user.id, vehicle_id)
    return paginated(await service.list_records(scope, query.filters(), page))


@router.get(
    VEHICLE_PATH,
    response_model=PaginatedResponse[MaintenanceRecordResponse],
    summary="Maintenance history of a vehicle",
)
async def list_records(
    ctx: VehicleViewer, service: RecordServiceDep, page: PageDep, query: MaintenanceQueryDep
) -> Any:
    scope = MaintenanceRecord.vehicle_id == ctx.vehicle_id
    return paginated(await service.list_records(scope, query.filters(), page))


@router.post(
    VEHICLE_PATH,
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[MaintenanceRecordResponse],
    summary="Record a maintenance or repair",
    description=(
        "Also advances the vehicle odometer when the record's mileage is the newest reading "
        "and moves the matching maintenance schedule forward."
    ),
)
async def create_record(
    body: MaintenanceRecordCreate, ctx: VehicleEditor, service: RecordServiceDep
) -> Any:
    return success(await service.create(ctx, body))


@router.get(
    f"{VEHICLE_PATH}/{{record_id}}",
    response_model=ApiResponse[MaintenanceRecordResponse],
    summary="Get a maintenance record",
)
async def get_record(record_id: uuid.UUID, ctx: VehicleViewer, service: RecordServiceDep) -> Any:
    return success(await service.get(ctx.vehicle_id, record_id))


@router.patch(
    f"{VEHICLE_PATH}/{{record_id}}",
    response_model=ApiResponse[MaintenanceRecordResponse],
    summary="Update a maintenance record",
)
async def update_record(
    record_id: uuid.UUID,
    body: MaintenanceRecordUpdate,
    ctx: VehicleEditor,
    service: RecordServiceDep,
) -> Any:
    return success(await service.update(ctx, record_id, body))


@router.delete(
    f"{VEHICLE_PATH}/{{record_id}}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a maintenance record",
)
async def delete_record(
    record_id: uuid.UUID, ctx: VehicleEditor, service: RecordServiceDep
) -> None:
    await service.delete(ctx, record_id)
