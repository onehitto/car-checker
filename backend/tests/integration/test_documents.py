"""Vehicle documents and expiration status (clock: 2026-10-06)."""

from typing import Any

import pytest
from httpx import AsyncClient

from tests.helpers import (
    API,
    AuthenticatedUser,
    create_document,
    create_vehicle,
    data,
    error,
)


@pytest.fixture
async def vehicle(client: AsyncClient, user: AuthenticatedUser) -> dict[str, Any]:
    return await create_vehicle(client, user)


def url(vehicle: dict[str, Any]) -> str:
    return f"{API}/vehicles/{vehicle['id']}/documents"


async def test_create_with_status(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    document = await create_document(
        client,
        user,
        vehicle["id"],
        document_number="POL-123",
        provider="Wafa Assurance",
        issue_date="2025-10-18",
        expiration_date="2026-10-18",
    )
    assert document["status"] == "expiring_soon"
    assert document["days_until_expiration"] == 12
    assert document["reminder_days"] == [30, 7, 1, 0]


async def test_statuses_and_custom_reminders(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    expired = await create_document(client, user, vehicle["id"], expiration_date="2026-09-30")
    far = await create_document(client, user, vehicle["id"], expiration_date="2026-12-20")
    custom = await create_document(
        client, user, vehicle["id"], expiration_date="2026-12-20", reminder_days=[7, 90, 30, 7]
    )
    none = await create_document(client, user, vehicle["id"], document_type="registration")
    assert expired["status"] == "expired"
    assert far["status"] == "valid"
    assert (custom["status"], custom["reminder_days"]) == ("expiring_soon", [90, 30, 7])
    assert (none["status"], none["days_until_expiration"]) == ("valid", None)

    async def titles_by_status(status: str) -> set[str]:
        body = (
            await client.get(url(vehicle), headers=user.headers, params={"status": status})
        ).json()
        return {d["id"] for d in body["data"]}

    # SQL filtering agrees with the computed status, including per-document windows.
    assert await titles_by_status("expired") == {expired["id"]}
    assert await titles_by_status("expiring_soon") == {custom["id"]}
    assert await titles_by_status("valid") == {far["id"], none["id"]}


async def test_validation(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    cases = [
        ({"issue_date": "2026-05-01", "expiration_date": "2026-01-01"}, "__root__"),
        ({"reminder_days": [400]}, "reminder_days"),
        ({"document_type": "passport"}, "document_type"),
        ({"title": ""}, "title"),
    ]
    for payload, field in cases:
        body = {"document_type": "insurance", "title": "Insurance", **payload}
        response = await client.post(url(vehicle), headers=user.headers, json=body)
        assert field in error(response, 422, "VALIDATION_ERROR")["fields"], payload


async def test_renewal_and_delete(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    document = await create_document(
        client, user, vehicle["id"], issue_date="2025-09-01", expiration_date="2026-09-30"
    )
    item = f"{url(vehicle)}/{document['id']}"
    renewed = data(
        await client.patch(
            item,
            headers=user.headers,
            json={"expiration_date": "2027-09-30", "title": "Insurance 2027"},
        )
    )
    assert (renewed["status"], renewed["title"]) == ("valid", "Insurance 2027")

    invalid = await client.patch(item, headers=user.headers, json={"expiration_date": "2025-01-01"})
    assert "expiration_date" in error(invalid, 422, "VALIDATION_ERROR")["fields"]

    assert (await client.delete(item, headers=user.headers)).status_code == 204
    error(await client.get(item, headers=user.headers), 404, "NOT_FOUND")


async def test_global_listing(
    client: AsyncClient,
    user: AuthenticatedUser,
    other_user: AuthenticatedUser,
    vehicle: dict[str, Any],
) -> None:
    second = await create_vehicle(client, user)
    await create_document(client, user, vehicle["id"], expiration_date="2026-10-10")
    await create_document(
        client,
        user,
        second["id"],
        document_type="technical_inspection",
        expiration_date="2026-10-20",
    )
    foreign = await create_vehicle(client, other_user)
    await create_document(client, other_user, foreign["id"], expiration_date="2026-10-08")

    body = (
        await client.get(
            f"{API}/documents", headers=user.headers, params={"status": "expiring_soon"}
        )
    ).json()
    assert [d["expiration_date"] for d in body["data"]] == ["2026-10-10", "2026-10-20"]
    inspections = (
        await client.get(
            f"{API}/documents",
            headers=user.headers,
            params={"document_type": "technical_inspection"},
        )
    ).json()
    assert inspections["meta"]["total"] == 1
