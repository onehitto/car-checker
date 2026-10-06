"""Router factory for type catalogs (maintenance types, part types).

Every catalog exposes the same five operations; system types are read-only and custom types
are private to their creator (see `CatalogService`).
"""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel

from app.api.deps import CurrentUser, DbSession
from app.api.openapi import AUTHENTICATED_ERRORS, error_responses
from app.core.pagination import SearchQuery
from app.core.responses import ApiResponse, success
from app.db.base import BaseModel as OrmModel
from app.modules.maintenance.catalog import CatalogService


def build_catalog_router(
    *,
    prefix: str,
    tag: str,
    model: type[OrmModel],
    resource: str,
    category_enum: type[Any],
    create_schema: type[BaseModel],
    update_schema: type[BaseModel],
    response_schema: type[BaseModel],
) -> APIRouter:
    router = APIRouter(prefix=prefix, tags=[tag], responses=AUTHENTICATED_ERRORS)
    label = resource.lower()

    def get_catalog(session: DbSession) -> CatalogService[Any]:
        return CatalogService(session, model, resource)

    catalog_dep = Annotated[CatalogService[Any], Depends(get_catalog)]

    @router.get(
        "",
        response_model=ApiResponse[list[response_schema]],  # type: ignore[valid-type]
        summary=f"List {label}s",
        description="System types (translated) followed by the caller's custom types.",
    )
    async def list_types(
        user: CurrentUser,
        catalog: catalog_dep,
        q: SearchQuery = None,
        category: Annotated[category_enum | None, Query()] = None,  # type: ignore[valid-type]
    ) -> Any:
        return success(await catalog.list_types(user.id, q=q, category=category))

    @router.post(
        "",
        status_code=status.HTTP_201_CREATED,
        response_model=ApiResponse[response_schema],  # type: ignore[valid-type]
        summary=f"Create a custom {label}",
        responses=error_responses(409),
    )
    async def create_type(
        body: create_schema,  # type: ignore[valid-type]
        user: CurrentUser,
        catalog: catalog_dep,
    ) -> Any:
        return success(await catalog.create(user.id, body))

    @router.get(
        "/{type_id}",
        response_model=ApiResponse[response_schema],  # type: ignore[valid-type]
        summary=f"Get a {label}",
        responses=error_responses(404),
    )
    async def get_type(
        type_id: uuid.UUID,
        user: CurrentUser,
        catalog: catalog_dep,
    ) -> Any:
        return success(await catalog.get_visible(user.id, type_id))

    @router.patch(
        "/{type_id}",
        response_model=ApiResponse[response_schema],  # type: ignore[valid-type]
        summary=f"Update a custom {label}",
        responses=error_responses(403, 404, 409),
    )
    async def update_type(
        type_id: uuid.UUID,
        body: update_schema,  # type: ignore[valid-type]
        user: CurrentUser,
        catalog: catalog_dep,
    ) -> Any:
        return success(await catalog.update(user.id, type_id, body))

    @router.delete(
        "/{type_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        summary=f"Delete a custom {label}",
        description="Refused with `TYPE_IN_USE` (409) while records use it.",
        responses=error_responses(403, 404, 409),
    )
    async def delete_type(
        type_id: uuid.UUID,
        user: CurrentUser,
        catalog: catalog_dep,
    ) -> None:
        await catalog.delete(user.id, type_id)

    return router
