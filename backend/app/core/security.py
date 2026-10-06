"""Password hashing, password policy, JWT access tokens and opaque token helpers."""

import hashlib
import hmac
import re
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import Settings
from app.core.ids import uuid7

# OWASP recommended Argon2id parameters (64 MiB, 3 iterations, 4 lanes).
_password_hasher = PasswordHasher(time_cost=3, memory_cost=64 * 1024, parallelism=4)

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128
ACCESS_TOKEN_TYPE = "access"  # noqa: S105 - token type claim, not a secret
OPAQUE_TOKEN_BYTES = 32  # 256 bits of entropy


# --- Passwords -------------------------------------------------------------------------------


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def password_needs_rehash(password_hash: str) -> bool:
    return _password_hasher.check_needs_rehash(password_hash)


# Verified against when the account does not exist, so response time does not reveal it.
DUMMY_PASSWORD_HASH = hash_password(secrets.token_urlsafe(16))


def password_policy_violation(password: str, email: str | None = None) -> str | None:
    """Return a human-readable reason when the password is not acceptable, else None."""
    if len(password) < PASSWORD_MIN_LENGTH:
        return f"Password must be at least {PASSWORD_MIN_LENGTH} characters long."
    if len(password) > PASSWORD_MAX_LENGTH:
        return f"Password must be at most {PASSWORD_MAX_LENGTH} characters long."
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        return "Password must contain at least one letter and one digit."
    if email:
        local_part = email.split("@", 1)[0].lower()
        if len(local_part) >= 3 and local_part in password.lower():
            return "Password must not contain your email address."
    return None


# --- JWT access tokens -------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AccessTokenClaims:
    user_id: uuid.UUID
    session_id: uuid.UUID
    expires_at: datetime


def create_access_token(
    settings: Settings,
    *,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    now: datetime | None = None,
    expires_in: int | None = None,
) -> str:
    issued_at = now or datetime.now(UTC)
    lifetime = settings.access_token_expires_in if expires_in is None else expires_in
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "sid": str(session_id),
        "type": ACCESS_TOKEN_TYPE,
        "jti": uuid7().hex,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": issued_at,
        "exp": issued_at + timedelta(seconds=lifetime),
    }
    return jwt.encode(
        payload, settings.jwt_secret.get_secret_value(), algorithm=settings.jwt_algorithm
    )


def decode_access_token(settings: Settings, token: str) -> AccessTokenClaims:
    """Validate signature, algorithm, issuer, audience, expiry and token type.

    Raises `jwt.ExpiredSignatureError` for expired tokens and `jwt.PyJWTError` otherwise.
    """
    payload = jwt.decode(
        token,
        settings.jwt_secret.get_secret_value(),
        algorithms=[settings.jwt_algorithm],
        audience=settings.jwt_audience,
        issuer=settings.jwt_issuer,
        options={"require": ["exp", "iat", "sub", "sid", "type", "jti", "iss", "aud"]},
        leeway=5,
    )
    if payload.get("type") != ACCESS_TOKEN_TYPE:
        raise jwt.InvalidTokenError("Unexpected token type")
    try:
        return AccessTokenClaims(
            user_id=uuid.UUID(payload["sub"]),
            session_id=uuid.UUID(payload["sid"]),
            expires_at=datetime.fromtimestamp(payload["exp"], UTC),
        )
    except (ValueError, TypeError) as exc:
        raise jwt.InvalidTokenError("Malformed claims") from exc


# --- Opaque tokens (refresh, password reset) ---------------------------------------------------


def generate_opaque_token() -> str:
    return secrets.token_urlsafe(OPAQUE_TOKEN_BYTES)


def hash_opaque_token(settings: Settings, token: str, purpose: str) -> str:
    """Keyed hash stored in the database; `purpose` separates token families."""
    key = settings.jwt_refresh_secret.get_secret_value().encode()
    return hmac.new(key, f"{purpose}:{token}".encode(), hashlib.sha256).hexdigest()
