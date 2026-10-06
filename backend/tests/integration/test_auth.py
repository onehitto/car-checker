"""Registration, login, token rotation and logout."""

import uuid
from collections.abc import Callable

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.security import create_access_token
from app.modules.audit.models import AuditLog
from tests.helpers import API, AuthenticatedUser, bearer, data, error, login, register_user

pytestmark = pytest.mark.asyncio


class TestRegister:
    async def test_creates_account_and_returns_tokens(self, client: AsyncClient) -> None:
        response = await client.post(
            f"{API}/auth/register",
            json={
                "email": "Amina@Example.com",
                "password": "S3cure-pass",
                "first_name": " Amina ",
                "last_name": "Benali",
                "preferred_language": "fr",
                "preferred_currency": "mad",
                "timezone": "Africa/Casablanca",
            },
        )
        body = data(response, 201)
        assert body["user"]["email"] == "amina@example.com"
        assert body["user"]["first_name"] == "Amina"
        assert body["user"]["preferred_currency"] == "MAD"
        assert body["user"]["preferred_language"] == "fr"
        assert "password_hash" not in body["user"]
        assert body["tokens"]["token_type"] == "bearer"
        assert body["tokens"]["expires_in"] == 900

    async def test_rejects_duplicate_email_case_insensitively(
        self, client: AsyncClient, user: AuthenticatedUser
    ) -> None:
        response = await client.post(
            f"{API}/auth/register",
            json={
                "email": user.email.upper(),
                "password": "An0ther-pass",
                "first_name": "X",
                "last_name": "Y",
            },
        )
        error(response, 409, "EMAIL_ALREADY_REGISTERED")

    @pytest.mark.parametrize(
        ("payload", "field"),
        [
            ({"password": "short1"}, "password"),
            ({"password": "no-digits-here"}, "password"),
            ({"email": "not-an-email"}, "email"),
            ({"preferred_currency": "EURO"}, "preferred_currency"),
            ({"timezone": "Mars/Base"}, "timezone"),
            ({"preferred_language": "de"}, "preferred_language"),
            ({"role": "admin"}, "role"),
        ],
    )
    async def test_validation_errors_name_the_field(
        self, client: AsyncClient, payload: dict[str, str], field: str
    ) -> None:
        base = {
            "email": "valid@example.com",
            "password": "S3cure-pass",
            "first_name": "A",
            "last_name": "B",
        }
        response = await client.post(f"{API}/auth/register", json={**base, **payload})
        err = error(response, 422, "VALIDATION_ERROR")
        assert field in err["fields"]


class TestLogin:
    async def test_login_with_valid_credentials(
        self, client: AsyncClient, user: AuthenticatedUser
    ) -> None:
        logged_in = await login(client, user.email.upper())
        assert logged_in.id == user.id
        assert logged_in.access_token != user.access_token

    async def test_wrong_password_and_unknown_email_look_identical(
        self, client: AsyncClient, user: AuthenticatedUser, db_session: AsyncSession
    ) -> None:
        wrong = await client.post(
            f"{API}/auth/login", json={"email": user.email, "password": "Wrong-pass1"}
        )
        unknown = await client.post(
            f"{API}/auth/login", json={"email": "nobody@example.com", "password": "Wrong-pass1"}
        )
        assert (
            error(wrong, 401, "INVALID_CREDENTIALS")["message"]
            == (error(unknown, 401, "INVALID_CREDENTIALS")["message"])
        )

        failures = (
            await db_session.scalars(select(AuditLog).where(AuditLog.action == "auth.login_failed"))
        ).all()
        assert {f.details["reason"] for f in failures} == {"wrong_password", "unknown_email"}
        assert all("nobody@example.com" not in str(f.details) for f in failures)

    async def test_login_rate_limit(self, app_factory: Callable[..., FastAPI]) -> None:
        app = app_factory(rate_limit_enabled=True, rate_limit_auth="2/minute")
        payload = {"email": "x@example.com", "password": "whatever1"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            statuses = [
                (await c.post(f"{API}/auth/login", json=payload)).status_code for _ in range(3)
            ]
        assert statuses == [401, 401, 429]


class TestTokens:
    async def test_access_token_grants_access(
        self, client: AsyncClient, user: AuthenticatedUser
    ) -> None:
        response = await client.post(f"{API}/auth/logout", headers=user.headers)
        assert response.status_code == 204

    async def test_missing_token(self, client: AsyncClient) -> None:
        response = await client.post(f"{API}/auth/logout")
        error(response, 401, "AUTHENTICATION_REQUIRED")
        assert response.headers["WWW-Authenticate"] == "Bearer"

    async def test_expired_token(
        self, client: AsyncClient, settings: Settings, user: AuthenticatedUser
    ) -> None:
        token = create_access_token(
            settings, user_id=uuid.UUID(user.id), session_id=uuid.uuid4(), expires_in=-60
        )
        error(await client.post(f"{API}/auth/logout", headers=bearer(token)), 401, "TOKEN_EXPIRED")

    async def test_token_for_unknown_session_is_rejected(
        self, client: AsyncClient, settings: Settings, user: AuthenticatedUser
    ) -> None:
        token = create_access_token(settings, user_id=uuid.UUID(user.id), session_id=uuid.uuid4())
        response = await client.post(f"{API}/auth/logout", headers=bearer(token))
        error(response, 401, "AUTHENTICATION_REQUIRED")

    async def test_garbage_token(self, client: AsyncClient) -> None:
        response = await client.post(f"{API}/auth/logout", headers=bearer("not.a.jwt"))
        error(response, 401, "AUTHENTICATION_REQUIRED")

    async def test_refresh_rotates_tokens(
        self, client: AsyncClient, user: AuthenticatedUser
    ) -> None:
        body = data(
            await client.post(f"{API}/auth/refresh", json={"refresh_token": user.refresh_token})
        )
        assert body["refresh_token"] != user.refresh_token
        assert (
            await client.post(f"{API}/auth/logout", headers=bearer(body["access_token"]))
        ).status_code == 204

    async def test_reusing_a_refresh_token_revokes_the_session(
        self, client: AsyncClient, user: AuthenticatedUser
    ) -> None:
        first = data(
            await client.post(f"{API}/auth/refresh", json={"refresh_token": user.refresh_token})
        )
        reuse = await client.post(f"{API}/auth/refresh", json={"refresh_token": user.refresh_token})
        error(reuse, 401, "INVALID_TOKEN")

        # The legitimate successor is now dead too, and so is the access token.
        error(
            await client.post(
                f"{API}/auth/refresh", json={"refresh_token": first["refresh_token"]}
            ),
            401,
            "INVALID_TOKEN",
        )
        error(
            await client.post(f"{API}/auth/logout", headers=bearer(first["access_token"])),
            401,
            "AUTHENTICATION_REQUIRED",
        )

    async def test_unknown_refresh_token(self, client: AsyncClient) -> None:
        response = await client.post(f"{API}/auth/refresh", json={"refresh_token": "x" * 43})
        error(response, 401, "INVALID_TOKEN")


class TestLogout:
    async def test_logout_revokes_access_and_refresh(
        self, client: AsyncClient, user: AuthenticatedUser
    ) -> None:
        assert (await client.post(f"{API}/auth/logout", headers=user.headers)).status_code == 204
        error(
            await client.post(f"{API}/auth/logout", headers=user.headers),
            401,
            "AUTHENTICATION_REQUIRED",
        )
        error(
            await client.post(f"{API}/auth/refresh", json={"refresh_token": user.refresh_token}),
            401,
            "INVALID_TOKEN",
        )

    async def test_logout_all_revokes_every_session(
        self, client: AsyncClient, user: AuthenticatedUser
    ) -> None:
        second = await login(client, user.email)
        assert (
            await client.post(f"{API}/auth/logout-all", headers=user.headers)
        ).status_code == 204
        for session in (user, second):
            error(
                await client.post(f"{API}/auth/logout", headers=session.headers),
                401,
                "AUTHENTICATION_REQUIRED",
            )

    async def test_other_users_are_not_affected(
        self, client: AsyncClient, user: AuthenticatedUser, other_user: AuthenticatedUser
    ) -> None:
        await client.post(f"{API}/auth/logout-all", headers=user.headers)
        assert (
            await client.post(f"{API}/auth/logout", headers=other_user.headers)
        ).status_code == 204


async def test_register_helper_creates_distinct_users(client: AsyncClient) -> None:
    first, second = await register_user(client), await register_user(client)
    assert first.id != second.id
