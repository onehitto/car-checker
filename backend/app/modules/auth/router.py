"""Authentication endpoints."""

from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, status

from app.api.deps import (
    AppSettings,
    ClockDep,
    CurrentAuth,
    DbSession,
    EmailSenderDep,
    RequestMetaDep,
)
from app.api.openapi import error_responses
from app.core.rate_limit import RateLimit
from app.core.responses import ApiResponse, success
from app.core.schemas import MessageResponse
from app.modules.auth.schemas import (
    AuthResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenPair,
)
from app.modules.auth.service import AuthService
from app.modules.notifications.email import send_safely

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


@router.post(
    "/password/forgot",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=ApiResponse[MessageResponse],
    summary="Request a password reset link",
    description=(
        "Always answers 202, whether or not the address belongs to an account, so the "
        "endpoint cannot be used to discover accounts. The link is valid for 30 minutes."
    ),
    responses=error_responses(422, 429),
    dependencies=[Depends(RateLimit("password_forgot", "auth"))],
)
async def forgot_password(
    body: ForgotPasswordRequest,
    service: AuthServiceDep,
    meta: RequestMetaDep,
    email_sender: EmailSenderDep,
    background_tasks: BackgroundTasks,
) -> Any:
    message = await service.request_password_reset(body.email, meta)
    if message is not None:
        background_tasks.add_task(send_safely, email_sender, message, kind="password_reset")
    return success({"message": "If an account exists for this email, a reset link has been sent."})


@router.post(
    "/password/reset",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Set a new password with a reset token",
    description="Signs out every session of the account.",
    responses=error_responses(401, 422, 429),
    dependencies=[Depends(RateLimit("password_reset", "auth"))],
)
async def reset_password(
    body: ResetPasswordRequest, service: AuthServiceDep, meta: RequestMetaDep
) -> None:
    await service.reset_password(body.token, body.new_password, meta)


@router.post(
    "/password/change",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change the password of the signed-in account",
    description="Keeps the current session and signs out all the others.",
    responses=error_responses(401, 422, 429),
    dependencies=[Depends(RateLimit("password_change", "auth"))],
)
async def change_password(
    body: ChangePasswordRequest,
    auth: CurrentAuth,
    service: AuthServiceDep,
    meta: RequestMetaDep,
    email_sender: EmailSenderDep,
    background_tasks: BackgroundTasks,
) -> None:
    notification = await service.change_password(
        auth.user, auth.session_id, body.current_password, body.new_password, meta
    )
    background_tasks.add_task(send_safely, email_sender, notification, kind="password_changed")
