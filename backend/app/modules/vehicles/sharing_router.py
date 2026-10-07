"""Vehicle sharing endpoints."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, status

from app.api.deps import ClockDep, DbSession, RequestMetaDep
from app.api.openapi import VEHICLE_ERRORS, error_responses
from app.core.rate_limit import RateLimit
from app.core.responses import ApiResponse, success
from app.modules.vehicles.access import VehicleOwner, VehicleViewer
from app.modules.vehicles.schemas import ShareCreate, ShareResponse, ShareUpdate
from app.modules.vehicles.sharing import SharingService

router = APIRouter(
    prefix="/vehicles/{vehicle_id}/access", tags=["Vehicle sharing"], responses=VEHICLE_ERRORS
)


def get_sharing_service(session: DbSession, clock: ClockDep) -> SharingService:
    return SharingService(session, clock)


SharingServiceDep = Annotated[SharingService, Depends(get_sharing_service)]


@router.get(
    "", response_model=ApiResponse[list[ShareResponse]], summary="Who can access the vehicle"
)
async def list_shares(ctx: VehicleOwner, service: SharingServiceDep) -> Any:
    return success(await service.list_shares(ctx))


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[ShareResponse],
    summary="Share the vehicle with a registered user",
    description="Owner only. Editors also receive the vehicle's alerts.",
    responses=error_responses(409),
    dependencies=[Depends(RateLimit("share", "auth"))],
)
async def share_vehicle(
    body: ShareCreate, ctx: VehicleOwner, service: SharingServiceDep, meta: RequestMetaDep
) -> Any:
    return success(await service.share(ctx, body, meta))


@router.patch(
    "/{access_id}", response_model=ApiResponse[ShareResponse], summary="Change a user's role"
)
async def update_share(
    access_id: uuid.UUID,
    body: ShareUpdate,
    ctx: VehicleOwner,
    service: SharingServiceDep,
    meta: RequestMetaDep,
) -> Any:
    return success(await service.update(ctx, access_id, body, meta))


@router.delete(
    "/{access_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke access (owner) or leave a shared vehicle (grantee)",
)
async def revoke_share(
    access_id: uuid.UUID, ctx: VehicleViewer, service: SharingServiceDep, meta: RequestMetaDep
) -> None:
    await service.revoke(ctx, access_id, meta)
