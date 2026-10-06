"""Garage endpoints."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, DbSession
from app.api.openapi import AUTHENTICATED_ERRORS, error_responses
from app.core.pagination import PageDep, SearchQuery, SortQuery, paginated
from app.core.responses import ApiResponse, PaginatedResponse, success
from app.modules.garages.models import GarageType
from app.modules.garages.schemas import GarageCreate, GarageResponse, GarageUpdate
from app.modules.garages.service import GarageFilters, GarageService

router = APIRouter(prefix="/garages", tags=["Garages"], responses=AUTHENTICATED_ERRORS)


def get_garage_service(session: DbSession) -> GarageService:
    return GarageService(session)


GarageServiceDep = Annotated[GarageService, Depends(get_garage_service)]


@router.get("", response_model=PaginatedResponse[GarageResponse], summary="List my garages")
async def list_garages(
    user: CurrentUser,
    service: GarageServiceDep,
    page: PageDep,
    q: SearchQuery = None,
    garage_type: Annotated[GarageType | None, Query()] = None,
    city: Annotated[str | None, Query(max_length=100)] = None,
    sort: SortQuery = None,
) -> Any:
    filters = GarageFilters(q=q, garage_type=garage_type, city=city, sort=sort)
    return paginated(await service.list_garages(user.id, filters, page))


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[GarageResponse],
    summary="Save a garage or service provider",
)
async def create_garage(body: GarageCreate, user: CurrentUser, service: GarageServiceDep) -> Any:
    return success(await service.create(user.id, body))


@router.get(
    "/{garage_id}",
    response_model=ApiResponse[GarageResponse],
    summary="Get a garage",
    responses=error_responses(404),
)
async def get_garage(garage_id: uuid.UUID, user: CurrentUser, service: GarageServiceDep) -> Any:
    return success(await service.get(user.id, garage_id))


@router.patch(
    "/{garage_id}",
    response_model=ApiResponse[GarageResponse],
    summary="Update a garage",
    responses=error_responses(404),
)
async def update_garage(
    garage_id: uuid.UUID, body: GarageUpdate, user: CurrentUser, service: GarageServiceDep
) -> Any:
    return success(await service.update(user.id, garage_id, body))


@router.delete(
    "/{garage_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a garage",
    description="Maintenance records and parts keep their history; their garage becomes empty.",
    responses=error_responses(404),
)
async def delete_garage(garage_id: uuid.UUID, user: CurrentUser, service: GarageServiceDep) -> None:
    await service.delete(user.id, garage_id)
