"""Fuel fill-up endpoints."""

import uuid
from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import ClockDep, DbSession
from app.api.openapi import VEHICLE_ERRORS
from app.core.pagination import PageDep, paginated
from app.core.responses import ApiResponse, PaginatedResponse, success
from app.core.units import ConsumptionUnit, DistanceUnit
from app.modules.fuel.models import PumpFuel
from app.modules.fuel.schemas import (
    FuelRecordCreate,
    FuelRecordResponse,
    FuelRecordUpdate,
    FuelStatisticsResponse,
)
from app.modules.fuel.service import FuelFilters, FuelService
from app.modules.vehicles.access import VehicleEditor, VehicleViewer

router = APIRouter(prefix="/vehicles/{vehicle_id}/fuel", tags=["Fuel"], responses=VEHICLE_ERRORS)


def get_fuel_service(session: DbSession, clock: ClockDep) -> FuelService:
    return FuelService(session, clock)


FuelServiceDep = Annotated[FuelService, Depends(get_fuel_service)]


@router.get(
    "",
    response_model=PaginatedResponse[FuelRecordResponse],
    summary="Fill-ups with per-fill consumption",
    description="Most recent first. Distances in km, consumption in L/100 km.",
)
async def list_fuel(
    ctx: VehicleViewer,
    service: FuelServiceDep,
    page: PageDep,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
    fuel_type: Annotated[PumpFuel | None, Query()] = None,
) -> Any:
    filters = FuelFilters(date_from=date_from, date_to=date_to, fuel_type=fuel_type)
    return paginated(await service.list_records(ctx, filters, page))


@router.get(
    "/statistics",
    response_model=ApiResponse[FuelStatisticsResponse],
    summary="Fuel statistics",
    description=(
        "Average and last consumption, fuel cost per distance unit and monthly spending. "
        "Units default to the caller's preferences."
    ),
)
async def fuel_statistics(
    ctx: VehicleViewer,
    service: FuelServiceDep,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
    distance_unit: Annotated[DistanceUnit | None, Query()] = None,
    consumption_unit: Annotated[ConsumptionUnit | None, Query()] = None,
) -> Any:
    stats = await service.statistics(
        ctx,
        date_from,
        date_to,
        distance_unit or ctx.user.preferred_distance_unit,
        consumption_unit or ctx.user.preferred_consumption_unit,
    )
    return success(stats)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[FuelRecordResponse],
    summary="Record a fill-up",
    description="Also records the cost as a fuel expense and advances the odometer.",
)
async def create_fuel(body: FuelRecordCreate, ctx: VehicleEditor, service: FuelServiceDep) -> Any:
    return success(await service.create(ctx, body))


@router.get("/{record_id}", response_model=ApiResponse[FuelRecordResponse], summary="Get a fill-up")
async def get_fuel(record_id: uuid.UUID, ctx: VehicleViewer, service: FuelServiceDep) -> Any:
    return success(await service.get_response(ctx, record_id))


@router.patch(
    "/{record_id}", response_model=ApiResponse[FuelRecordResponse], summary="Update a fill-up"
)
async def update_fuel(
    record_id: uuid.UUID, body: FuelRecordUpdate, ctx: VehicleEditor, service: FuelServiceDep
) -> Any:
    return success(await service.update(ctx, record_id, body))


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a fill-up")
async def delete_fuel(record_id: uuid.UUID, ctx: VehicleEditor, service: FuelServiceDep) -> None:
    await service.delete(ctx, record_id)
