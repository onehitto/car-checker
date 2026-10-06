"""Maintenance type catalog: system types + private custom types."""

from typing import Any

from httpx import AsyncClient

from app.db.seeds import MAINTENANCE_TYPES
from tests.helpers import API, AuthenticatedUser, data, error, register_user

URL = f"{API}/maintenance-types"


async def list_types(client: AsyncClient, user: AuthenticatedUser, **params: Any) -> list[Any]:
    return list(data(await client.get(URL, headers=user.headers, params=params)))


async def test_system_types_are_seeded(client: AsyncClient, user: AuthenticatedUser) -> None:
    types = await list_types(client, user)
    codes = {t["code"] for t in types}
    assert codes == {seed.code for seed in MAINTENANCE_TYPES}
    oil = next(t for t in types if t["code"] == "oil_change")
    assert oil["is_system"] is True
    assert (oil["default_interval_km"], oil["default_interval_months"]) == (10_000, 12)


async def test_system_type_names_follow_user_language(client: AsyncClient) -> None:
    french = await register_user(client, preferred_language="fr")
    arabic = await register_user(client, preferred_language="ar")
    assert any(t["name"] == "Vidange" for t in await list_types(client, french))
    assert any(t["name"] == "تغيير الزيت" for t in await list_types(client, arabic))


async def test_custom_type_lifecycle(
    client: AsyncClient, user: AuthenticatedUser, other_user: AuthenticatedUser
) -> None:
    created = data(
        await client.post(
            URL,
            headers=user.headers,
            json={
                "name": "Diesel particulate filter",
                "category": "filters",
                "default_interval_km": 120_000,
            },
        ),
        201,
    )
    assert created["is_system"] is False
    assert created["code"] is None

    # Private to its creator; listed after system types.
    assert (await list_types(client, user))[-1]["id"] == created["id"]
    assert created["id"] not in {t["id"] for t in await list_types(client, other_user)}
    error(await client.get(f"{URL}/{created['id']}", headers=other_user.headers), 404, "NOT_FOUND")

    updated = data(
        await client.patch(
            f"{URL}/{created['id']}", headers=user.headers, json={"name": "DPF cleaning"}
        )
    )
    assert updated["name"] == "DPF cleaning"

    duplicate = await client.post(URL, headers=user.headers, json={"name": "DPF cleaning"})
    error(duplicate, 409, "CONFLICT")

    assert (await client.delete(f"{URL}/{created['id']}", headers=user.headers)).status_code == 204


async def test_system_types_are_read_only(client: AsyncClient, user: AuthenticatedUser) -> None:
    oil = next(t for t in await list_types(client, user) if t["code"] == "oil_change")
    error(
        await client.patch(f"{URL}/{oil['id']}", headers=user.headers, json={"name": "x"}),
        403,
        "FORBIDDEN",
    )
    error(await client.delete(f"{URL}/{oil['id']}", headers=user.headers), 403, "FORBIDDEN")


async def test_filters(client: AsyncClient, user: AuthenticatedUser) -> None:
    brakes = await list_types(client, user, category="brakes")
    assert {t["code"] for t in brakes} == {"brake_pads", "brake_discs"}
    assert [t["code"] for t in await list_types(client, user, q="timing")] == [
        "timing_belt",
        "timing_chain",
    ]
