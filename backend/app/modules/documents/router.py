"""Vehicle document endpoints (per vehicle and across all accessible vehicles)."""

import uuid
from dataclasses import dataclass
from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import ClockDep, CurrentUser, DbSession
from app.api.openapi import VEHICLE_ERRORS
from app.core.pagination import PageDep, SearchQuery, paginated
from app.core.responses import ApiResponse, PaginatedResponse, success
from app.modules.documents.expiration import DocumentStatus
from app.modules.documents.models import DocumentType, VehicleDocument
from app.modules.documents.schemas import DocumentCreate, DocumentResponse, DocumentUpdate
from app.modules.documents.service import DocumentFilters, DocumentService, to_response
from app.modules.vehicles.access import VehicleEditor, VehicleViewer, accessible_vehicles_clause

router = APIRouter(tags=["Documents"], responses=VEHICLE_ERRORS)

VEHICLE_PATH = "/vehicles/{vehicle_id}/documents"


def get_document_service(session: DbSession, clock: ClockDep) -> DocumentService:
    return DocumentService(session, clock)


DocumentServiceDep = Annotated[DocumentService, Depends(get_document_service)]


@dataclass
class DocumentQuery:
    document_type: Annotated[DocumentType | None, Query()] = None
    status: Annotated[DocumentStatus | None, Query(description="valid, expiring_soon, expired")] = (
        None
    )
    expires_before: Annotated[date | None, Query()] = None
    q: SearchQuery = None
    sort: Annotated[
        str | None,
        Query(max_length=200, description="expiration_date, issue_date, title, created_at"),
    ] = None

    def filters(self) -> DocumentFilters:
        return DocumentFilters(**self.__dict__)


DocumentQueryDep = Annotated[DocumentQuery, Depends()]


@router.get(
    "/documents",
    response_model=PaginatedResponse[DocumentResponse],
    summary="Documents of all my vehicles",
    description="Use `status=expiring_soon` or `status=expired` to find documents to renew.",
)
async def list_all_documents(
    user: CurrentUser,
    clock: ClockDep,
    service: DocumentServiceDep,
    page: PageDep,
    query: DocumentQueryDep,
    vehicle_id: Annotated[uuid.UUID | None, Query()] = None,
) -> Any:
    scope = accessible_vehicles_clause(VehicleDocument.vehicle_id, user.id, vehicle_id)
    today = clock.today(user.timezone)
    return paginated(await service.list_documents(scope, query.filters(), page, today))


@router.get(
    VEHICLE_PATH,
    response_model=PaginatedResponse[DocumentResponse],
    summary="Documents of a vehicle",
)
async def list_documents(
    ctx: VehicleViewer,
    clock: ClockDep,
    service: DocumentServiceDep,
    page: PageDep,
    query: DocumentQueryDep,
) -> Any:
    scope = VehicleDocument.vehicle_id == ctx.vehicle_id
    today = clock.today(ctx.user.timezone)
    return paginated(await service.list_documents(scope, query.filters(), page, today))


@router.post(
    VEHICLE_PATH,
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[DocumentResponse],
    summary="Add a document",
)
async def create_document(
    body: DocumentCreate, ctx: VehicleEditor, clock: ClockDep, service: DocumentServiceDep
) -> Any:
    document = await service.create(ctx, body)
    return success(to_response(document, clock.today(ctx.user.timezone)))


@router.get(
    f"{VEHICLE_PATH}/{{document_id}}",
    response_model=ApiResponse[DocumentResponse],
    summary="Get a document",
)
async def get_document(
    document_id: uuid.UUID, ctx: VehicleViewer, clock: ClockDep, service: DocumentServiceDep
) -> Any:
    document = await service.get(ctx.vehicle_id, document_id)
    return success(to_response(document, clock.today(ctx.user.timezone)))


@router.patch(
    f"{VEHICLE_PATH}/{{document_id}}",
    response_model=ApiResponse[DocumentResponse],
    summary="Update or renew a document",
)
async def update_document(
    document_id: uuid.UUID,
    body: DocumentUpdate,
    ctx: VehicleEditor,
    clock: ClockDep,
    service: DocumentServiceDep,
) -> Any:
    document = await service.update(ctx, document_id, body)
    return success(to_response(document, clock.today(ctx.user.timezone)))


@router.delete(
    f"{VEHICLE_PATH}/{{document_id}}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document",
)
async def delete_document(
    document_id: uuid.UUID, ctx: VehicleEditor, service: DocumentServiceDep
) -> None:
    await service.delete(ctx, document_id)
