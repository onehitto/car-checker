"""Authentication use cases: registration, login, token rotation, logout, passwords."""

import asyncio
import hashlib
import uuid
from dataclasses import dataclass
from datetime import timedelta
from urllib.parse import urlencode

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock
from app.core.config import Settings
from app.core.exceptions import (
    AuthenticationError,
    ConflictError,
    InvalidCredentialsError,
    InvalidTokenError,
    ValidationAppError,
)
from app.core.i18n import translate
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    dummy_password_hash,
    generate_opaque_token,
    hash_opaque_token,
    hash_password,
    password_needs_rehash,
    password_policy_violation,
    verify_password,
)
from app.modules.audit.service import RequestMeta, record_audit
from app.modules.auth.models import PasswordResetToken, RefreshToken, UserSession
from app.modules.auth.schemas import RegisterRequest
from app.modules.notifications.email import EmailMessage
from app.modules.users.models import User

logger = get_logger(__name__)

REFRESH_PURPOSE = "refresh"
RESET_PURPOSE = "password_reset"


@dataclass(frozen=True, slots=True)
class IssuedTokens:
    access_token: str
    refresh_token: str
    expires_in: int
    refresh_expires_in: int


def email_fingerprint(email: str) -> str:
    """Correlates failed attempts in the audit log without storing the address itself."""
    return hashlib.sha256(email.encode()).hexdigest()[:16]


async def find_user_by_email(session: AsyncSession, email: str) -> User | None:
    result = await session.scalars(select(User).where(User.email == email.lower()))
    return result.one_or_none()


async def revoke_user_sessions(
    session: AsyncSession, user_id: uuid.UUID, clock: Clock, *, keep: uuid.UUID | None = None
) -> None:
    stmt = (
        update(UserSession)
        .where(UserSession.user_id == user_id, UserSession.revoked_at.is_(None))
        .values(revoked_at=clock.now())
    )
    if keep is not None:
        stmt = stmt.where(UserSession.id != keep)
    await session.execute(stmt)


class AuthService:
    def __init__(self, session: AsyncSession, settings: Settings, clock: Clock) -> None:
        self.session = session
        self.settings = settings
        self.clock = clock

    # --- Registration & login ------------------------------------------------------------------

    async def register(self, data: RegisterRequest, meta: RequestMeta) -> tuple[User, IssuedTokens]:
        if await find_user_by_email(self.session, data.email):
            raise self._email_taken()
        user = User(
            email=data.email,
            password_hash=await asyncio.to_thread(hash_password, data.password),
            first_name=data.first_name,
            last_name=data.last_name,
            phone_number=data.phone_number,
            preferred_language=data.preferred_language,
            preferred_currency=data.preferred_currency,
            preferred_distance_unit=data.preferred_distance_unit,
            preferred_consumption_unit=data.preferred_consumption_unit,
            timezone=data.timezone,
            password_changed_at=self.clock.now(),
        )
        self.session.add(user)
        try:
            await self.session.flush()
        except IntegrityError:
            await self.session.rollback()
            raise self._email_taken() from None

        tokens = await self._open_session(user, meta)
        record_audit(self.session, "auth.register", user_id=user.id, meta=meta)
        await self.session.commit()
        logger.info("user_registered", user_id=str(user.id))
        return user, tokens

    async def login(
        self, email: str, password: str, meta: RequestMeta
    ) -> tuple[User, IssuedTokens]:
        user = await find_user_by_email(self.session, email)
        if user is None:
            await asyncio.to_thread(verify_password, dummy_password_hash(), password)
            await self._login_failed(None, "unknown_email", meta, email)
        elif not await asyncio.to_thread(verify_password, user.password_hash, password):
            await self._login_failed(user.id, "wrong_password", meta, email)
        assert user is not None  # noqa: S101 - _login_failed always raises
        if not user.is_active:
            await self._login_failed(user.id, "account_disabled", meta, email)

        if password_needs_rehash(user.password_hash):
            user.password_hash = await asyncio.to_thread(hash_password, password)
        user.last_login_at = self.clock.now()
        tokens = await self._open_session(user, meta)
        record_audit(self.session, "auth.login", user_id=user.id, meta=meta)
        await self.session.commit()
        return user, tokens

    async def _login_failed(
        self, user_id: uuid.UUID | None, reason: str, meta: RequestMeta, email: str
    ) -> None:
        record_audit(
            self.session,
            "auth.login_failed",
            user_id=user_id,
            meta=meta,
            details={"reason": reason, "email_fingerprint": email_fingerprint(email)},
        )
        await self.session.commit()
        logger.warning("auth_login_failed", reason=reason, user_id=str(user_id))
        if reason == "account_disabled":
            raise AuthenticationError("This account is disabled.", code="ACCOUNT_DISABLED")
        raise InvalidCredentialsError()

    # --- Sessions & tokens -----------------------------------------------------------------------

    async def refresh(self, raw_token: str, meta: RequestMeta) -> IssuedTokens:
        now = self.clock.now()
        token_hash = hash_opaque_token(self.settings, raw_token, REFRESH_PURPOSE)
        row = (
            await self.session.execute(
                select(RefreshToken, UserSession, User)
                .join(UserSession, RefreshToken.session_id == UserSession.id)
                .join(User, UserSession.user_id == User.id)
                .where(RefreshToken.token_hash == token_hash)
                .with_for_update(of=RefreshToken)
            )
        ).one_or_none()
        if row is None:
            logger.warning("auth_refresh_failed", reason="unknown_token")
            raise InvalidTokenError()
        token, user_session, user = row

        if token.used_at is not None:
            # A rotated token was presented again: it leaked. Kill the whole session.
            if user_session.revoked_at is None:
                user_session.revoked_at = now
            record_audit(
                self.session,
                "auth.refresh_token_reused",
                user_id=user.id,
                meta=meta,
                entity_type="user_session",
                entity_id=user_session.id,
            )
            await self.session.commit()
            logger.warning("auth_refresh_token_reused", user_id=str(user.id))
            raise InvalidTokenError()

        if (
            token.expires_at <= now
            or user_session.revoked_at is not None
            or user_session.expires_at <= now
            or not user.is_active
        ):
            logger.warning("auth_refresh_failed", reason="expired_or_revoked")
            raise InvalidTokenError()

        token.used_at = now
        user_session.last_used_at = now
        user_session.expires_at = now + timedelta(seconds=self.settings.refresh_token_expires_in)
        if meta.ip_address:
            user_session.ip_address = meta.ip_address
        tokens = self._issue_tokens(user.id, user_session)
        await self.session.commit()
        return tokens

    async def logout(self, user_id: uuid.UUID, session_id: uuid.UUID, meta: RequestMeta) -> None:
        await self.session.execute(
            update(UserSession)
            .where(UserSession.id == session_id, UserSession.user_id == user_id)
            .values(revoked_at=self.clock.now())
        )
        record_audit(self.session, "auth.logout", user_id=user_id, meta=meta)
        await self.session.commit()

    async def logout_all(self, user_id: uuid.UUID, meta: RequestMeta) -> None:
        await revoke_user_sessions(self.session, user_id, self.clock)
        record_audit(self.session, "auth.logout_all", user_id=user_id, meta=meta)
        await self.session.commit()

    async def _open_session(self, user: User, meta: RequestMeta) -> IssuedTokens:
        now = self.clock.now()
        user_session = UserSession(
            user_id=user.id,
            user_agent=meta.user_agent,
            ip_address=meta.ip_address,
            last_used_at=now,
            expires_at=now + timedelta(seconds=self.settings.refresh_token_expires_in),
        )
        self.session.add(user_session)
        return self._issue_tokens(user.id, user_session)

    def _issue_tokens(self, user_id: uuid.UUID, user_session: UserSession) -> IssuedTokens:
        raw_refresh = generate_opaque_token()
        self.session.add(
            RefreshToken(
                session_id=user_session.id,
                token_hash=hash_opaque_token(self.settings, raw_refresh, REFRESH_PURPOSE),
                expires_at=self.clock.now()
                + timedelta(seconds=self.settings.refresh_token_expires_in),
            )
        )
        return IssuedTokens(
            access_token=create_access_token(
                self.settings, user_id=user_id, session_id=user_session.id
            ),
            refresh_token=raw_refresh,
            expires_in=self.settings.access_token_expires_in,
            refresh_expires_in=self.settings.refresh_token_expires_in,
        )

    # --- Passwords -------------------------------------------------------------------------------

    async def request_password_reset(self, email: str, meta: RequestMeta) -> EmailMessage | None:
        """Create a reset token and return the email to send (None when nothing to send).

        The caller answers 202 in every case so the endpoint does not reveal accounts.
        """
        user = await find_user_by_email(self.session, email)
        if user is None or not user.is_active:
            logger.info("password_reset_requested", outcome="ignored")
            return None

        now = self.clock.now()
        # Only the most recent link stays valid.
        await self.session.execute(
            update(PasswordResetToken)
            .where(PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None))
            .values(used_at=now)
        )
        raw_token = generate_opaque_token()
        self.session.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=hash_opaque_token(self.settings, raw_token, RESET_PURPOSE),
                expires_at=now + timedelta(seconds=self.settings.password_reset_expires_in),
            )
        )
        record_audit(self.session, "auth.password_reset_requested", user_id=user.id, meta=meta)
        await self.session.commit()

        reset_url = (
            f"{self.settings.frontend_url.rstrip('/')}{self.settings.password_reset_path}"
            f"?{urlencode({'token': raw_token})}"
        )
        language = user.preferred_language
        return EmailMessage(
            to=user.email,
            subject=translate("email.password_reset.subject", language),
            body=translate(
                "email.password_reset.body",
                language,
                first_name=user.first_name,
                reset_url=reset_url,
                expires_minutes=self.settings.password_reset_expires_in // 60,
            ),
        )

    async def reset_password(self, raw_token: str, new_password: str, meta: RequestMeta) -> None:
        now = self.clock.now()
        token_hash = hash_opaque_token(self.settings, raw_token, RESET_PURPOSE)
        row = (
            await self.session.execute(
                select(PasswordResetToken, User)
                .join(User, PasswordResetToken.user_id == User.id)
                .where(PasswordResetToken.token_hash == token_hash)
                .with_for_update(of=PasswordResetToken)
            )
        ).one_or_none()
        if row is None:
            raise InvalidTokenError("The reset link is invalid or has expired.")
        reset_token, user = row
        if reset_token.used_at is not None or reset_token.expires_at <= now or not user.is_active:
            raise InvalidTokenError("The reset link is invalid or has expired.")

        self._check_new_password(new_password, user.email)
        reset_token.used_at = now
        await self._set_password(user, new_password)
        await revoke_user_sessions(self.session, user.id, self.clock)
        record_audit(self.session, "auth.password_reset", user_id=user.id, meta=meta)
        await self.session.commit()

    async def change_password(
        self,
        user: User,
        session_id: uuid.UUID,
        current_password: str,
        new_password: str,
        meta: RequestMeta,
    ) -> EmailMessage:
        if not await asyncio.to_thread(verify_password, user.password_hash, current_password):
            raise ValidationAppError(fields={"current_password": "Current password is incorrect."})
        if current_password == new_password:
            raise ValidationAppError(
                fields={"new_password": "New password must differ from the current one."}
            )
        self._check_new_password(new_password, user.email)
        await self._set_password(user, new_password)
        await revoke_user_sessions(self.session, user.id, self.clock, keep=session_id)
        record_audit(self.session, "auth.password_changed", user_id=user.id, meta=meta)
        await self.session.commit()
        return EmailMessage(
            to=user.email,
            subject=translate("email.password_changed.subject", user.preferred_language),
            body=translate(
                "email.password_changed.body", user.preferred_language, first_name=user.first_name
            ),
        )

    @staticmethod
    def _check_new_password(password: str, email: str) -> None:
        violation = password_policy_violation(password, email)
        if violation:
            raise ValidationAppError(fields={"new_password": violation})

    async def _set_password(self, user: User, password: str) -> None:
        user.password_hash = await asyncio.to_thread(hash_password, password)
        user.password_changed_at = self.clock.now()

    @staticmethod
    def _email_taken() -> ConflictError:
        return ConflictError(
            "An account with this email already exists.", code="EMAIL_ALREADY_REGISTERED"
        )
