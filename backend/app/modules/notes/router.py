"""Note endpoints."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import DbSession
from app.api.openapi import VEHICLE_ERRORS
from app.core.pagination import PageDep, SearchQuery, paginated
from app.core.responses import ApiResponse, PaginatedResponse, success
from app.modules.notes.models import NoteCategory, NoteEntity
from app.modules.notes.schemas import NoteCreate, NoteResponse, NoteUpdate
from app.modules.notes.service import NoteFilters, NoteService
from app.modules.vehicles.access import VehicleEditor, VehicleViewer

router = APIRouter(prefix="/vehicles/{vehicle_id}/notes", tags=["Notes"], responses=VEHICLE_ERRORS)


def get_note_service(session: DbSession) -> NoteService:
    return NoteService(session)


NoteServiceDep = Annotated[NoteService, Depends(get_note_service)]


@router.get(
    "",
    response_model=PaginatedResponse[NoteResponse],
    summary="Notes of a vehicle",
    description="Pinned notes first, then the most recent.",
)
async def list_notes(
    ctx: VehicleViewer,
    service: NoteServiceDep,
    page: PageDep,
    category: Annotated[NoteCategory | None, Query()] = None,
    entity_type: Annotated[NoteEntity | None, Query()] = None,
    entity_id: Annotated[uuid.UUID | None, Query()] = None,
    pinned: Annotated[bool | None, Query()] = None,
    q: SearchQuery = None,
) -> Any:
    filters = NoteFilters(
        category=category, entity_type=entity_type, entity_id=entity_id, pinned=pinned, q=q
    )
    return paginated(await service.list_notes(ctx, filters, page))


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[NoteResponse],
    summary="Add a note",
)
async def create_note(body: NoteCreate, ctx: VehicleEditor, service: NoteServiceDep) -> Any:
    return success(await service.create(ctx, body))


@router.get("/{note_id}", response_model=ApiResponse[NoteResponse], summary="Get a note")
async def get_note(note_id: uuid.UUID, ctx: VehicleViewer, service: NoteServiceDep) -> Any:
    return success(await service.get(ctx, note_id))


@router.patch("/{note_id}", response_model=ApiResponse[NoteResponse], summary="Update a note")
async def update_note(
    note_id: uuid.UUID, body: NoteUpdate, ctx: VehicleEditor, service: NoteServiceDep
) -> Any:
    return success(await service.update(ctx, note_id, body))


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a note")
async def delete_note(note_id: uuid.UUID, ctx: VehicleEditor, service: NoteServiceDep) -> None:
    await service.delete(ctx, note_id)
