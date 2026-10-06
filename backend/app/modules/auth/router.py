"""Authentication endpoints."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, status

from app.api.deps import AppSettings, ClockDep, CurrentAuth, DbSession, RequestMetaDep
from app.api.openapi import error_responses
from app.core.rate_limit import RateLimit
from app.core.responses import ApiResponse, success
from app.modules.auth.schemas import (
    AuthResponse,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
)
from app.modules.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])


def get_auth_service(session: DbSession, settings: AppSettings, clock: ClockDep) -> AuthService:
    return AuthService(session, settings, clock)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[AuthResponse],
    summary="Create an account",
    description="Creates the account and signs it in (returns a token pair).",
    responses=error_responses(409, 422, 429),
    dependencies=[Depends(RateLimit("register", "auth"))],
)
async def register(body: RegisterRequest, service: AuthServiceDep, meta: RequestMetaDep) -> Any:
    user, tokens = await service.register(body, meta)
    return success({"user": user, "tokens": tokens})


@router.post(
    "/login",
    response_model=ApiResponse[AuthResponse],
    summary="Sign in with email and password",
    responses=error_responses(401, 422, 429),
    dependencies=[Depends(RateLimit("login", "auth"))],
)
async def login(body: LoginRequest, service: AuthServiceDep, meta: RequestMetaDep) -> Any:
    user, tokens = await service.login(body.email, body.password, meta)
    return success({"user": user, "tokens": tokens})


@router.post(
    "/refresh",
    response_model=ApiResponse[TokenPair],
    summary="Rotate the refresh token",
    description=(
        "Exchanges a refresh token for a new token pair. Each refresh token can be used once; "
        "presenting a used token revokes the whole session."
    ),
    responses=error_responses(401, 422, 429),
    dependencies=[Depends(RateLimit("refresh", "auth"))],
)
async def refresh(body: RefreshRequest, service: AuthServiceDep, meta: RequestMetaDep) -> Any:
    return success(await service.refresh(body.refresh_token, meta))


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Sign out the current session",
    responses=error_responses(401),
)
async def logout(auth: CurrentAuth, service: AuthServiceDep, meta: RequestMetaDep) -> None:
    await service.logout(auth.user.id, auth.session_id, meta)


@router.post(
    "/logout-all",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Sign out every session of the account",
    responses=error_responses(401),
)
async def logout_all(auth: CurrentAuth, service: AuthServiceDep, meta: RequestMetaDep) -> None:
    await service.logout_all(auth.user.id, meta)
