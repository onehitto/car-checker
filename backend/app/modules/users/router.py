"""Endpoints of the signed-in user (`/users/me`)."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, status

from app.api.deps import ClockDep, CurrentAuth, CurrentUser, DbSession, RequestMetaDep
from app.api.openapi import AUTHENTICATED_ERRORS, error_responses
from app.core.responses import ApiResponse, success
from app.modules.users.schemas import (
    DeleteAccountRequest,
    SessionResponse,
    UserResponse,
    UserUpdate,
)
from app.modules.users.service import UserService

router = APIRouter(prefix="/users/me", tags=["Users"], responses=AUTHENTICATED_ERRORS)


def get_user_service(session: DbSession, clock: ClockDep) -> UserService:
    return UserService(session, clock)


UserServiceDep = Annotated[UserService, Depends(get_user_service)]


@router.get("", response_model=ApiResponse[UserResponse], summary="Get my profile")
async def get_me(user: CurrentUser) -> Any:
    return success(user)


@router.patch("", response_model=ApiResponse[UserResponse], summary="Update my profile")
async def update_me(body: UserUpdate, user: CurrentUser, service: UserServiceDep) -> Any:
    return success(await service.update_profile(user, body))


@router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete my account",
    description=(
        "Permanently deletes the account, its vehicles and their complete history. "
        "Requires the current password."
    ),
)
async def delete_me(
    body: DeleteAccountRequest, user: CurrentUser, service: UserServiceDep, meta: RequestMetaDep
) -> None:
    await service.delete_account(user, body.password, meta)


@router.get(
    "/sessions",
    response_model=ApiResponse[list[SessionResponse]],
    summary="List my active sessions",
)
async def list_sessions(auth: CurrentAuth, service: UserServiceDep) -> Any:
    return success(await service.list_sessions(auth.user.id, auth.session_id))


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke one of my sessions",
    responses=error_responses(404),
)
async def revoke_session(
    session_id: uuid.UUID, auth: CurrentAuth, service: UserServiceDep, meta: RequestMetaDep
) -> None:
    await service.revoke_session(auth.user.id, session_id, meta)
