"""HTTP helpers shared by integration tests."""

import uuid
from dataclasses import dataclass
from typing import Any

from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession

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


VEHICLE_PAYLOAD: dict[str, Any] = {
    "brand": "Dacia",
    "model": "Logan",
    "year": 2019,
    "fuel_type": "diesel",
    "initial_mileage": 80_000,
    "current_mileage": 80_000,
}


async def create_vehicle(
    client: AsyncClient, owner: AuthenticatedUser, **fields: Any
) -> dict[str, Any]:
    payload = {**VEHICLE_PAYLOAD, **fields}
    result: dict[str, Any] = data(
        await client.post(f"{API}/vehicles", headers=owner.headers, json=payload), 201
    )
    return result


async def share_vehicle_in_db(
    session: AsyncSession, vehicle_id: str, user_id: str, role: str
) -> None:
    """Grant access directly in the database (independent from the sharing endpoints)."""
    from app.modules.vehicles.models import SharedRole, VehicleAccess

    session.add(
        VehicleAccess(
            vehicle_id=uuid.UUID(vehicle_id), user_id=uuid.UUID(user_id), role=SharedRole(role)
        )
    )
    await session.commit()


async def create_garage(
    client: AsyncClient, user: AuthenticatedUser, **fields: Any
) -> dict[str, Any]:
    payload = {"name": "Garage Atlas", "city": "Casablanca", **fields}
    result: dict[str, Any] = data(
        await client.post(f"{API}/garages", headers=user.headers, json=payload), 201
    )
    return result


async def maintenance_type_id(client: AsyncClient, user: AuthenticatedUser, code: str) -> str:
    types = data(await client.get(f"{API}/maintenance-types", headers=user.headers))
    return str(next(t["id"] for t in types if t["code"] == code))


async def create_maintenance(
    client: AsyncClient,
    user: AuthenticatedUser,
    vehicle_id: str,
    *,
    code: str = "oil_change",
    **fields: Any,
) -> dict[str, Any]:
    payload = {
        "maintenance_type_id": await maintenance_type_id(client, user, code),
        "service_date": "2026-09-01",
        **fields,
    }
    result: dict[str, Any] = data(
        await client.post(
            f"{API}/vehicles/{vehicle_id}/maintenance", headers=user.headers, json=payload
        ),
        201,
    )
    return result


async def part_type_id(client: AsyncClient, user: AuthenticatedUser, code: str) -> str:
    types = data(await client.get(f"{API}/part-types", headers=user.headers))
    return str(next(t["id"] for t in types if t["code"] == code))


async def create_part(
    client: AsyncClient,
    user: AuthenticatedUser,
    vehicle_id: str,
    *,
    code: str = "brake_pads",
    **fields: Any,
) -> dict[str, Any]:
    payload = {
        "part_type_id": await part_type_id(client, user, code),
        "installed_date": "2026-01-10",
        **fields,
    }
    result: dict[str, Any] = data(
        await client.post(f"{API}/vehicles/{vehicle_id}/parts", headers=user.headers, json=payload),
        201,
    )
    return result


async def create_document(
    client: AsyncClient, user: AuthenticatedUser, vehicle_id: str, **fields: Any
) -> dict[str, Any]:
    payload = {"document_type": "insurance", "title": "Insurance 2026", **fields}
    result: dict[str, Any] = data(
        await client.post(
            f"{API}/vehicles/{vehicle_id}/documents", headers=user.headers, json=payload
        ),
        201,
    )
    return result


async def create_expense(
    client: AsyncClient, user: AuthenticatedUser, vehicle_id: str, **fields: Any
) -> dict[str, Any]:
    payload = {
        "category": "parking",
        "title": "Parking",
        "amount": "20.00",
        "expense_date": "2026-09-15",
        **fields,
    }
    result: dict[str, Any] = data(
        await client.post(
            f"{API}/vehicles/{vehicle_id}/expenses", headers=user.headers, json=payload
        ),
        201,
    )
    return result
