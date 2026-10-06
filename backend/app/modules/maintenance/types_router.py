"""Maintenance type catalog endpoints."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, DbSession
from app.api.openapi import AUTHENTICATED_ERRORS, error_responses
from app.core.pagination import SearchQuery
from app.core.responses import ApiResponse, success
from app.db.catalog import localized
from app.modules.maintenance.catalog import CatalogService
from app.modules.maintenance.models import MaintenanceCategory, MaintenanceType
from app.modules.maintenance.schemas import (
    MaintenanceTypeCreate,
    MaintenanceTypeResponse,
    MaintenanceTypeUpdate,
)

router = APIRouter(
    prefix="/maintenance-types", tags=["Maintenance types"], responses=AUTHENTICATED_ERRORS
)


def get_catalog(session: DbSession) -> CatalogService[MaintenanceType]:
    return CatalogService(session, MaintenanceType, "Maintenance type")


CatalogDep = Annotated[CatalogService[MaintenanceType], Depends(get_catalog)]


@router.get(
    "",
    response_model=ApiResponse[list[MaintenanceTypeResponse]],
    summary="List maintenance types",
    description="System types (translated) followed by the caller's custom types.",
)
async def list_types(
    user: CurrentUser,
    catalog: CatalogDep,
    q: SearchQuery = None,
    category: Annotated[MaintenanceCategory | None, Query()] = None,
) -> Any:
    items = await catalog.list_types(user.id, q=q, category=category)
    language = user.preferred_language
    return success([localized(MaintenanceTypeResponse, item, language) for item in items])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[MaintenanceTypeResponse],
    summary="Create a custom maintenance type",
    responses=error_responses(409),
)
async def create_type(body: MaintenanceTypeCreate, user: CurrentUser, catalog: CatalogDep) -> Any:
    item = await catalog.create(user.id, body)
    return success(localized(MaintenanceTypeResponse, item, user.preferred_language))


@router.get(
    "/{type_id}",
    response_model=ApiResponse[MaintenanceTypeResponse],
    summary="Get a maintenance type",
    responses=error_responses(404),
)
async def get_type(type_id: uuid.UUID, user: CurrentUser, catalog: CatalogDep) -> Any:
    item = await catalog.get_visible(user.id, type_id)
    return success(localized(MaintenanceTypeResponse, item, user.preferred_language))


@router.patch(
    "/{type_id}",
    response_model=ApiResponse[MaintenanceTypeResponse],
    summary="Update a custom maintenance type",
    responses=error_responses(403, 404, 409),
)
async def update_type(
    type_id: uuid.UUID, body: MaintenanceTypeUpdate, user: CurrentUser, catalog: CatalogDep
) -> Any:
    item = await catalog.update(user.id, type_id, body)
    return success(localized(MaintenanceTypeResponse, item, user.preferred_language))


@router.delete(
    "/{type_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a custom maintenance type",
    description="Refused with `TYPE_IN_USE` (409) while records or schedules use it.",
    responses=error_responses(403, 404, 409),
)
async def delete_type(type_id: uuid.UUID, user: CurrentUser, catalog: CatalogDep) -> None:
    await catalog.delete(user.id, type_id)
