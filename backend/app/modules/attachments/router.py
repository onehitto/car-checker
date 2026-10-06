"""Attachment endpoints and the vehicle picture."""

import uuid
from typing import Annotated, Any
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.responses import StreamingResponse

from app.api.deps import AppSettings, ClockDep, DbSession, StorageDep
from app.api.openapi import VEHICLE_ERRORS, error_responses
from app.core.pagination import PageDep, paginated
from app.core.rate_limit import RateLimit
from app.core.responses import ApiResponse, PaginatedResponse, success
from app.modules.attachments.models import AttachmentEntity
from app.modules.attachments.schemas import AttachmentResponse
from app.modules.attachments.service import AttachmentService, UploadedFile
from app.modules.vehicles.access import VehicleEditor, VehicleViewer

router = APIRouter(tags=["Attachments"], responses=VEHICLE_ERRORS)

PATH = "/vehicles/{vehicle_id}/attachments"
UPLOAD_ERRORS = error_responses(413, 415)


def get_attachment_service(
    session: DbSession, storage: StorageDep, settings: AppSettings, clock: ClockDep
) -> AttachmentService:
    return AttachmentService(session, storage, settings, clock)


AttachmentServiceDep = Annotated[AttachmentService, Depends(get_attachment_service)]


async def read_upload(file: UploadFile) -> UploadedFile:
    return UploadedFile(file_name=file.filename, content=await file.read())


@router.get(
    PATH,
    response_model=PaginatedResponse[AttachmentResponse],
    summary="Files attached to a vehicle or one of its records",
)
async def list_attachments(
    ctx: VehicleViewer,
    service: AttachmentServiceDep,
    page: PageDep,
    entity_type: Annotated[AttachmentEntity | None, Query()] = None,
    entity_id: Annotated[uuid.UUID | None, Query()] = None,
) -> Any:
    return paginated(await service.list_attachments(ctx, entity_type, entity_id, page))


@router.post(
    PATH,
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[AttachmentResponse],
    summary="Upload a file",
    description=(
        "`multipart/form-data` with `file`, `entity_type` and `entity_id` (the record of this "
        "vehicle the file belongs to; omit it for `vehicle`). PDF, JPEG, PNG, WebP or HEIC, "
        "detected from the content."
    ),
    responses=UPLOAD_ERRORS,
    dependencies=[Depends(RateLimit("upload", "upload"))],
)
async def upload_attachment(
    ctx: VehicleEditor,
    service: AttachmentServiceDep,
    file: Annotated[UploadFile, File(description="The file to upload.")],
    entity_type: Annotated[AttachmentEntity, Form()],
    entity_id: Annotated[uuid.UUID | None, Form()] = None,
) -> Any:
    return success(await service.upload(ctx, entity_type, entity_id, await read_upload(file)))


@router.get(
    f"{PATH}/{{attachment_id}}",
    response_model=ApiResponse[AttachmentResponse],
    summary="Attachment metadata",
)
async def get_attachment(
    attachment_id: uuid.UUID, ctx: VehicleViewer, service: AttachmentServiceDep
) -> Any:
    return success(await service.get(ctx, attachment_id))


@router.get(
    f"{PATH}/{{attachment_id}}/download",
    response_class=StreamingResponse,
    summary="Download a file",
    responses={200: {"content": {"application/octet-stream": {}}, "description": "File content"}},
)
async def download_attachment(
    attachment_id: uuid.UUID, ctx: VehicleViewer, service: AttachmentServiceDep
) -> StreamingResponse:
    attachment, content = await service.open(ctx, attachment_id)
    return StreamingResponse(
        content,
        media_type=attachment.content_type,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(attachment.file_name)}",
            "Content-Length": str(attachment.file_size),
            "Cache-Control": "private, no-store",
        },
    )


@router.delete(
    f"{PATH}/{{attachment_id}}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a file",
)
async def delete_attachment(
    attachment_id: uuid.UUID, ctx: VehicleEditor, service: AttachmentServiceDep
) -> None:
    await service.delete(ctx, attachment_id)


@router.put(
    "/vehicles/{vehicle_id}/image",
    response_model=ApiResponse[AttachmentResponse],
    summary="Upload or replace the vehicle picture",
    description="JPEG, PNG, WebP or HEIC. The vehicle's `image_attachment_id` points to it.",
    responses=UPLOAD_ERRORS,
    dependencies=[Depends(RateLimit("upload", "upload"))],
)
async def set_vehicle_image(
    ctx: VehicleEditor,
    service: AttachmentServiceDep,
    file: Annotated[UploadFile, File(description="The picture.")],
) -> Any:
    return success(await service.set_vehicle_image(ctx, await read_upload(file)))


@router.delete(
    "/vehicles/{vehicle_id}/image",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove the vehicle picture",
)
async def remove_vehicle_image(ctx: VehicleEditor, service: AttachmentServiceDep) -> None:
    await service.remove_vehicle_image(ctx)
