"""Sessions and opaque tokens (refresh, password reset)."""

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel
from app.modules.users.models import User


class UserSession(BaseModel):
    """A signed-in device. Its id is the `sid` claim of access tokens."""

    __tablename__ = "user_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    user_agent: Mapped[str | None] = mapped_column(sa.String(512))
    ip_address: Mapped[str | None] = mapped_column(INET)
    last_used_at: Mapped[datetime]
    expires_at: Mapped[datetime]
    revoked_at: Mapped[datetime | None]

    user: Mapped[User] = relationship(lazy="raise")


class RefreshToken(BaseModel):
    """Rotating refresh token of a session. Only an HMAC of the token is stored."""

    __tablename__ = "refresh_tokens"

    session_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("user_sessions.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(sa.CHAR(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(index=True)
    used_at: Mapped[datetime | None]

    session: Mapped[UserSession] = relationship(lazy="raise")


class PasswordResetToken(BaseModel):
    __tablename__ = "password_reset_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(sa.CHAR(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(index=True)
    used_at: Mapped[datetime | None]

    user: Mapped[User] = relationship(lazy="raise")
