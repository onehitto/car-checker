import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    generate_opaque_token,
    hash_opaque_token,
    hash_password,
    password_needs_rehash,
    password_policy_violation,
    verify_password,
)


@pytest.fixture
def settings() -> Settings:
    return Settings(_env_file=None)  # type: ignore[call-arg]


class TestPasswords:
    def test_hash_is_argon2id_and_verifies(self) -> None:
        hashed = hash_password("S3cure-pass")
        assert hashed.startswith("$argon2id$")
        assert verify_password(hashed, "S3cure-pass")
        assert not verify_password(hashed, "wrong-pass1")
        assert not password_needs_rehash(hashed)

    def test_invalid_hash_never_verifies(self) -> None:
        assert not verify_password("not-a-hash", "whatever1")

    @pytest.mark.parametrize(
        ("password", "email", "reason"),
        [
            ("short1", None, "at least 8"),
            ("a1" * 65, None, "at most 128"),
            ("onlyletters", None, "letter and one digit"),
            ("1234567890", None, "letter and one digit"),
            ("amina2026!", "amina@example.com", "email"),
        ],
    )
    def test_policy_rejections(self, password: str, email: str | None, reason: str) -> None:
        violation = password_policy_violation(password, email)
        assert violation is not None
        assert reason in violation

    def test_policy_accepts_reasonable_password(self) -> None:
        assert password_policy_violation("S3cure-pass", "amina@example.com") is None


class TestAccessTokens:
    def test_round_trip(self, settings: Settings) -> None:
        user_id, session_id = uuid.uuid4(), uuid.uuid4()
        token = create_access_token(settings, user_id=user_id, session_id=session_id)
        claims = decode_access_token(settings, token)
        assert (claims.user_id, claims.session_id) == (user_id, session_id)

    def test_expired_token_is_rejected(self, settings: Settings) -> None:
        token = create_access_token(
            settings,
            user_id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            now=datetime.now(UTC) - timedelta(hours=1),
        )
        with pytest.raises(jwt.ExpiredSignatureError):
            decode_access_token(settings, token)

    def test_token_signed_with_another_key_is_rejected(self, settings: Settings) -> None:
        other = settings.model_copy(update={"jwt_secret": SecretStr("another-" + "x" * 40)})
        token = create_access_token(other, user_id=uuid.uuid4(), session_id=uuid.uuid4())
        with pytest.raises(jwt.InvalidSignatureError):
            decode_access_token(settings, token)

    def test_unsigned_token_is_rejected(self, settings: Settings) -> None:
        now = datetime.now(UTC)
        token = jwt.encode(
            {
                "sub": str(uuid.uuid4()),
                "sid": str(uuid.uuid4()),
                "type": "access",
                "jti": "x",
                "iss": settings.jwt_issuer,
                "aud": settings.jwt_audience,
                "iat": now,
                "exp": now + timedelta(minutes=5),
            },
            key=None,
            algorithm="none",
        )
        with pytest.raises(jwt.PyJWTError):
            decode_access_token(settings, token)

    def test_wrong_audience_is_rejected(self, settings: Settings) -> None:
        other = settings.model_copy(update={"jwt_audience": "someone-else"})
        token = create_access_token(other, user_id=uuid.uuid4(), session_id=uuid.uuid4())
        with pytest.raises(jwt.InvalidAudienceError):
            decode_access_token(settings, token)


class TestOpaqueTokens:
    def test_tokens_are_random_and_long(self) -> None:
        tokens = {generate_opaque_token() for _ in range(100)}
        assert len(tokens) == 100
        assert all(len(token) >= 43 for token in tokens)

    def test_hash_is_keyed_and_purpose_bound(self, settings: Settings) -> None:
        token = generate_opaque_token()
        refresh_hash = hash_opaque_token(settings, token, "refresh")
        assert len(refresh_hash) == 64
        assert refresh_hash == hash_opaque_token(settings, token, "refresh")
        assert refresh_hash != hash_opaque_token(settings, token, "password_reset")
        other = settings.model_copy(update={"jwt_refresh_secret": SecretStr("z" * 48)})
        assert refresh_hash != hash_opaque_token(other, token, "refresh")
