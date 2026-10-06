"""Password reset and password change flows."""

import re
from datetime import timedelta

from fastapi import FastAPI
from httpx import AsyncClient

from app.core.clock import FixedClock
from app.modules.notifications.email import MemoryEmailSender
from tests.helpers import API, AuthenticatedUser, data, error, login

NEW_PASSWORD = "N3w-password"


def outbox(app: FastAPI) -> MemoryEmailSender:
    sender = app.state.email_sender
    assert isinstance(sender, MemoryEmailSender)
    return sender


def reset_token_from_email(app: FastAPI) -> str:
    match = re.search(r"token=([A-Za-z0-9_\-]+)", outbox(app).outbox[-1].body)
    assert match
    return match.group(1)


async def forgot(client: AsyncClient, email: str) -> None:
    body = data(await client.post(f"{API}/auth/password/forgot", json={"email": email}), 202)
    assert "reset link" in body["message"]


class TestPasswordReset:
    async def test_full_reset_flow(
        self, client: AsyncClient, app: FastAPI, user: AuthenticatedUser
    ) -> None:
        await forgot(client, user.email)
        message = outbox(app).outbox[-1]
        assert message.to == user.email
        assert "http://localhost:3000/reset-password?token=" in message.body

        token = reset_token_from_email(app)
        response = await client.post(
            f"{API}/auth/password/reset", json={"token": token, "new_password": NEW_PASSWORD}
        )
        assert response.status_code == 204

        # Every previous session is signed out; the new password works, the old one does not.
        error(
            await client.post(f"{API}/auth/logout", headers=user.headers),
            401,
            "AUTHENTICATION_REQUIRED",
        )
        await login(client, user.email, NEW_PASSWORD)
        error(
            await client.post(
                f"{API}/auth/login", json={"email": user.email, "password": user.password}
            ),
            401,
            "INVALID_CREDENTIALS",
        )

    async def test_token_is_single_use(
        self, client: AsyncClient, app: FastAPI, user: AuthenticatedUser
    ) -> None:
        await forgot(client, user.email)
        token = reset_token_from_email(app)
        payload = {"token": token, "new_password": NEW_PASSWORD}
        assert (await client.post(f"{API}/auth/password/reset", json=payload)).status_code == 204
        error(await client.post(f"{API}/auth/password/reset", json=payload), 401, "INVALID_TOKEN")

    async def test_only_latest_link_is_valid(
        self, client: AsyncClient, app: FastAPI, user: AuthenticatedUser
    ) -> None:
        await forgot(client, user.email)
        first = reset_token_from_email(app)
        await forgot(client, user.email)
        response = await client.post(
            f"{API}/auth/password/reset", json={"token": first, "new_password": NEW_PASSWORD}
        )
        error(response, 401, "INVALID_TOKEN")

    async def test_expired_token_is_rejected(
        self, client: AsyncClient, app: FastAPI, user: AuthenticatedUser, clock: FixedClock
    ) -> None:
        await forgot(client, user.email)
        token = reset_token_from_email(app)
        clock.set(clock.now() + timedelta(minutes=31))
        response = await client.post(
            f"{API}/auth/password/reset", json={"token": token, "new_password": NEW_PASSWORD}
        )
        error(response, 401, "INVALID_TOKEN")

    async def test_weak_new_password_is_rejected(
        self, client: AsyncClient, app: FastAPI, user: AuthenticatedUser
    ) -> None:
        await forgot(client, user.email)
        response = await client.post(
            f"{API}/auth/password/reset",
            json={"token": reset_token_from_email(app), "new_password": "weak"},
        )
        assert "new_password" in error(response, 422, "VALIDATION_ERROR")["fields"]

    async def test_unknown_email_gets_same_answer_and_no_email(
        self, client: AsyncClient, app: FastAPI
    ) -> None:
        await forgot(client, "nobody@example.com")
        assert outbox(app).outbox == []


class TestPasswordChange:
    async def test_change_keeps_current_session_and_revokes_others(
        self, client: AsyncClient, app: FastAPI, user: AuthenticatedUser
    ) -> None:
        other_device = await login(client, user.email)
        response = await client.post(
            f"{API}/auth/password/change",
            headers=user.headers,
            json={"current_password": user.password, "new_password": NEW_PASSWORD},
        )
        assert response.status_code == 204

        assert (await client.post(f"{API}/auth/logout", headers=user.headers)).status_code == 204
        error(
            await client.post(f"{API}/auth/logout", headers=other_device.headers),
            401,
            "AUTHENTICATION_REQUIRED",
        )
        await login(client, user.email, NEW_PASSWORD)
        assert "password" in outbox(app).outbox[-1].subject.lower()

    async def test_wrong_current_password(
        self, client: AsyncClient, user: AuthenticatedUser
    ) -> None:
        response = await client.post(
            f"{API}/auth/password/change",
            headers=user.headers,
            json={"current_password": "Wrong-pass1", "new_password": NEW_PASSWORD},
        )
        assert "current_password" in error(response, 422, "VALIDATION_ERROR")["fields"]

    async def test_new_password_must_differ(
        self, client: AsyncClient, user: AuthenticatedUser
    ) -> None:
        response = await client.post(
            f"{API}/auth/password/change",
            headers=user.headers,
            json={"current_password": user.password, "new_password": user.password},
        )
        assert "new_password" in error(response, 422, "VALIDATION_ERROR")["fields"]

    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.post(
            f"{API}/auth/password/change",
            json={"current_password": "x", "new_password": NEW_PASSWORD},
        )
        error(response, 401, "AUTHENTICATION_REQUIRED")
