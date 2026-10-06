"""HTTP helpers shared by integration tests."""

import uuid
from dataclasses import dataclass
from typing import Any

from httpx import AsyncClient, Response

API = "/api/v1"
DEFAULT_PASSWORD = "S3cure-pass"


@dataclass
class AuthenticatedUser:
    id: str
    email: str
    access_token: str
    refresh_token: str
    password: str = DEFAULT_PASSWORD

    @property
    def headers(self) -> dict[str, str]:
        return bearer(self.access_token)


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def data(response: Response, status_code: int = 200) -> Any:
    """Assert the status code and the success envelope, then return `data`."""
    assert response.status_code == status_code, response.text
    body = response.json()
    assert body["success"] is True
    return body["data"]


def error(response: Response, status_code: int, code: str) -> dict[str, Any]:
    """Assert an error envelope with the given status and code; return the error object."""
    assert response.status_code == status_code, response.text
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == code, body
    return dict(body["error"])


async def register_user(
    client: AsyncClient,
    *,
    email: str | None = None,
    password: str = DEFAULT_PASSWORD,
    **fields: Any,
) -> AuthenticatedUser:
    payload = {
        "email": email or f"user-{uuid.uuid4().hex[:10]}@example.com",
        "password": password,
        "first_name": "Test",
        "last_name": "User",
        **fields,
    }
    body = data(await client.post(f"{API}/auth/register", json=payload), 201)
    return AuthenticatedUser(
        id=body["user"]["id"],
        email=body["user"]["email"],
        access_token=body["tokens"]["access_token"],
        refresh_token=body["tokens"]["refresh_token"],
        password=password,
    )


async def login(
    client: AsyncClient, email: str, password: str = DEFAULT_PASSWORD
) -> AuthenticatedUser:
    body = data(await client.post(f"{API}/auth/login", json={"email": email, "password": password}))
    return AuthenticatedUser(
        id=body["user"]["id"],
        email=body["user"]["email"],
        access_token=body["tokens"]["access_token"],
        refresh_token=body["tokens"]["refresh_token"],
        password=password,
    )
