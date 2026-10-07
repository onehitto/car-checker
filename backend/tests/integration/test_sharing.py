"""Vehicle sharing endpoints and the resulting permissions."""

from typing import Any

import pytest
from httpx import AsyncClient

from tests.helpers import (
    API,
    AuthenticatedUser,
    create_vehicle,
    data,
    error,
    maintenance_type_id,
    register_user,
)


@pytest.fixture
async def vehicle(client: AsyncClient, user: AuthenticatedUser) -> dict[str, Any]:
    return await create_vehicle(client, user, initial_mileage=40_000, current_mileage=59_400)


def url(vehicle: dict[str, Any]) -> str:
    return f"{API}/vehicles/{vehicle['id']}/access"


async def share(
    client: AsyncClient, owner: AuthenticatedUser, vehicle: dict[str, Any], email: str, role: str
) -> Any:
    return await client.post(
        url(vehicle), headers=owner.headers, json={"email": email, "role": role}
    )


async def test_share_list_update_revoke(
    client: AsyncClient,
    user: AuthenticatedUser,
    other_user: AuthenticatedUser,
    vehicle: dict[str, Any],
) -> None:
    grant = data(await share(client, user, vehicle, other_user.email.upper(), "viewer"), 201)
    assert (grant["user"]["id"], grant["role"], grant["granted_by_id"]) == (
        other_user.id,
        "viewer",
        user.id,
    )

    shares = data(await client.get(url(vehicle), headers=user.headers))
    assert [s["id"] for s in shares] == [grant["id"]]
    seen = data(await client.get(f"{API}/vehicles/{vehicle['id']}", headers=other_user.headers))
    assert seen["access_role"] == "viewer"

    data(
        await client.patch(
            f"{url(vehicle)}/{grant['id']}", headers=user.headers, json={"role": "editor"}
        )
    )
    edited = await client.patch(
        f"{API}/vehicles/{vehicle['id']}", headers=other_user.headers, json={"color": "blue"}
    )
    assert data(edited)["color"] == "blue"

    assert (
        await client.delete(f"{url(vehicle)}/{grant['id']}", headers=user.headers)
    ).status_code == 204
    error(
        await client.get(f"{API}/vehicles/{vehicle['id']}", headers=other_user.headers),
        404,
        "NOT_FOUND",
    )


async def test_share_rules(
    client: AsyncClient,
    user: AuthenticatedUser,
    other_user: AuthenticatedUser,
    vehicle: dict[str, Any],
) -> None:
    error(await share(client, user, vehicle, "nobody@example.com", "viewer"), 404, "NOT_FOUND")
    assert (
        "email"
        in error(await share(client, user, vehicle, user.email, "viewer"), 422, "VALIDATION_ERROR")[
            "fields"
        ]
    )
    assert (
        "role"
        in error(
            await share(client, user, vehicle, other_user.email, "owner"), 422, "VALIDATION_ERROR"
        )["fields"]
    )
    data(await share(client, user, vehicle, other_user.email, "editor"), 201)
    error(await share(client, user, vehicle, other_user.email, "viewer"), 409, "ALREADY_SHARED")

    # Editors cannot manage sharing.
    third = await register_user(client)
    error(await share(client, other_user, vehicle, third.email, "viewer"), 403, "FORBIDDEN")
    error(await client.get(url(vehicle), headers=other_user.headers), 403, "FORBIDDEN")


async def test_grantee_can_leave_but_not_remove_others(
    client: AsyncClient,
    user: AuthenticatedUser,
    other_user: AuthenticatedUser,
    vehicle: dict[str, Any],
) -> None:
    third = await register_user(client)
    mine = data(await share(client, user, vehicle, other_user.email, "viewer"), 201)
    theirs = data(await share(client, user, vehicle, third.email, "viewer"), 201)
    error(
        await client.delete(f"{url(vehicle)}/{theirs['id']}", headers=other_user.headers),
        403,
        "FORBIDDEN",
    )
    assert (
        await client.delete(f"{url(vehicle)}/{mine['id']}", headers=other_user.headers)
    ).status_code == 204
    listed = (await client.get(f"{API}/vehicles", headers=other_user.headers)).json()
    assert listed["meta"]["total"] == 0


async def test_editors_receive_alerts_until_revoked(
    client: AsyncClient,
    user: AuthenticatedUser,
    other_user: AuthenticatedUser,
    vehicle: dict[str, Any],
) -> None:
    await client.post(
        f"{API}/vehicles/{vehicle['id']}/maintenance-schedules",
        headers=user.headers,
        json={
            "maintenance_type_id": await maintenance_type_id(client, user, "oil_change"),
            "last_service_date": "2025-11-01",
            "last_service_mileage": 50_000,
        },
    )
    grant = data(await share(client, user, vehicle, other_user.email, "editor"), 201)
    open_alerts = {"status": ["active", "read"]}
    assert (
        await client.get(f"{API}/alerts", headers=other_user.headers, params=open_alerts)
    ).json()["meta"]["total"] == 1

    await client.delete(f"{url(vehicle)}/{grant['id']}", headers=user.headers)
    assert (
        await client.get(f"{API}/alerts", headers=other_user.headers, params=open_alerts)
    ).json()["meta"]["total"] == 0
