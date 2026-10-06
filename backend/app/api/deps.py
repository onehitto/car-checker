"""Common FastAPI dependencies."""

import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Annotated

import jwt
import structlog
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock, get_clock
from app.core.config import Settings
from app.core.exceptions import AuthenticationError
from app.core.i18n import set_current_language
from app.core.security import decode_access_token
from app.db.session import Database
from app.modules.audit.service import RequestMeta
from app.modules.auth.models import UserSession
from app.modules.notifications.email import EmailSender
from app.modules.users.models import User


async def get_db(request: Request) -> AsyncIterator[AsyncSession]:
    """One session per request. Services commit explicitly; uncommitted work is rolled back."""
    database: Database = request.app.state.db
    async with database.session_factory() as session:
        yield session


def get_app_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


DbSession = Annotated[AsyncSession, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_app_settings)]
ClockDep = Annotated[Clock, Depends(get_clock)]


# --- Authentication ------------------------------------------------------------------------

bearer_scheme = HTTPBearer(
    auto_error=False,
    description="Access token returned by `/api/v1/auth/login` or `/api/v1/auth/refresh`.",
)


@dataclass(frozen=True, slots=True)
class AuthContext:
    user: User
    session_id: uuid.UUID


async def get_auth_context(
    session: DbSession,
    settings: AppSettings,
    clock: ClockDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> AuthContext:
    """Validate the bearer token and load the user with its (non-revoked) session."""
    if credentials is None:
        raise AuthenticationError()
    try:
        claims = decode_access_token(settings, credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("The access token has expired.", code="TOKEN_EXPIRED") from None
    except jwt.PyJWTError:
        raise AuthenticationError("The access token is invalid.") from None

    user = (
        await session.scalars(
            select(User)
            .join(UserSession, UserSession.user_id == User.id)
            .where(
                User.id == claims.user_id,
                User.is_active.is_(True),
                UserSession.id == claims.session_id,
                UserSession.revoked_at.is_(None),
                UserSession.expires_at > clock.now(),
            )
        )
    ).one_or_none()
    if user is None:
        raise AuthenticationError("The session is no longer valid. Please sign in again.")

    structlog.contextvars.bind_contextvars(user_id=str(user.id))
    set_current_language(user.preferred_language)
    return AuthContext(user=user, session_id=claims.session_id)


CurrentAuth = Annotated[AuthContext, Depends(get_auth_context)]


async def get_current_user(auth: CurrentAuth) -> User:
    return auth.user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_request_meta(request: Request) -> RequestMeta:
    return RequestMeta.build(
        request.client.host if request.client else None, request.headers.get("user-agent")
    )


RequestMetaDep = Annotated[RequestMeta, Depends(get_request_meta)]


def get_email_sender(request: Request) -> EmailSender:
    sender: EmailSender = request.app.state.email_sender
    return sender


EmailSenderDep = Annotated[EmailSender, Depends(get_email_sender)]
