"""Vehicle CRUD and per-vehicle authorization."""

from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers import (
    API,
    AuthenticatedUser,
    create_vehicle,
    data,
    error,
    register_user,
    share_vehicle_in_db,
)


class TestCreate:
    async def test_create_with_defaults(self, client: AsyncClient, user: AuthenticatedUser) -> None:
        vehicle = await create_vehicle(
            client,
            user,
            license_plate=" 12345-a-6 ",
            vin="uu1lsdaah12345678",
            current_mileage=None,
            initial_mileage=81_000,
        )
        assert vehicle["owner_id"] == user.id
        assert vehicle["access_role"] == "owner"
        assert vehicle["currency"] == "EUR"
        assert vehicle["current_mileage"] == 81_000
        assert vehicle["license_plate"] == "12345-A-6"
        assert vehicle["vin"] == "UU1LSDAAH12345678"
        assert vehicle["display_name"] == "Dacia Logan"
        assert vehicle["status"] == "active"

    async def test_currency_defaults_to_owner_preference(self, client: AsyncClient) -> None:
        owner = await register_user(client, preferred_currency="MAD")
        assert (await create_vehicle(client, owner))["currency"] == "MAD"

    @pytest.mark.parametrize(
        ("fields", "field"),
        [
            ({"year": 1800}, "year"),
            ({"year": 2028}, "year"),
            ({"vin": "WVWZZZ1JZ3W38652I"}, "vin"),
            ({"vin": "ab"}, "vin"),
            ({"fuel_type": "steam"}, "fuel_type"),
            ({"initial_mileage": -1}, "initial_mileage"),
            ({"initial_mileage": 90_000, "current_mileage": 80_000}, "__root__"),
            ({"purchase_price": "-5"}, "purchase_price"),
            ({"purchase_price": "10.123"}, "purchase_price"),
            ({"purchase_date": "2027-01-01"}, "purchase_date"),
            ({"owner_id": "00000000-0000-0000-0000-000000000000"}, "owner_id"),
        ],
    )
    async def test_validation(
        self, client: AsyncClient, user: AuthenticatedUser, fields: dict[str, Any], field: str
    ) -> None:
        response = await client.post(
            f"{API}/vehicles",
            headers=user.headers,
            json={
                "brand": "Dacia",
                "model": "Logan",
                "year": 2019,
                "fuel_type": "diesel",
                **fields,
            },
        )
        assert field in error(response, 422, "VALIDATION_ERROR")["fields"]

    async def test_duplicate_vin_for_same_owner(
        self, client: AsyncClient, user: AuthenticatedUser, other_user: AuthenticatedUser
    ) -> None:
        await create_vehicle(client, user, vin="UU1LSDAAH12345678")
        response = await client.post(
            f"{API}/vehicles",
            headers=user.headers,
            json={
                "brand": "X",
                "model": "Y",
                "year": 2020,
                "fuel_type": "petrol",
                "vin": "UU1LSDAAH12345678",
            },
        )
        error(response, 409, "VIN_ALREADY_REGISTERED")
        # Another owner (e.g. the next buyer) may register the same VIN.
        await create_vehicle(client, other_user, vin="UU1LSDAAH12345678")


class TestReadUpdateDelete:
    async def test_get_update_delete(self, client: AsyncClient, user: AuthenticatedUser) -> None:
        vehicle = await create_vehicle(client, user)
        url = f"{API}/vehicles/{vehicle['id']}"
        assert data(await client.get(url, headers=user.headers))["id"] == vehicle["id"]

        updated = data(
            await client.patch(
                url, headers=user.headers, json={"nickname": "Family car", "status": "sold"}
            )
        )
        assert updated["display_name"] == "Family car"
        assert updated["status"] == "sold"
        assert updated["brand"] == "Dacia"

        assert (await client.delete(url, headers=user.headers)).status_code == 204
        error(await client.get(url, headers=user.headers), 404, "NOT_FOUND")

    async def test_update_rules(self, client: AsyncClient, user: AuthenticatedUser) -> None:
        vehicle = await create_vehicle(client, user)
        url = f"{API}/vehicles/{vehicle['id']}"
        for payload, field in (
            ({"brand": None}, "brand"),
            ({"initial_mileage": 90_000}, "initial_mileage"),
            ({"current_mileage": 90_000}, "current_mileage"),
        ):
            response = await client.patch(url, headers=user.headers, json=payload)
            assert field in error(response, 422, "VALIDATION_ERROR")["fields"]


class TestList:
    async def test_lists_only_accessible_vehicles(
        self, client: AsyncClient, user: AuthenticatedUser, other_user: AuthenticatedUser
    ) -> None:
        mine = await create_vehicle(client, user, brand="Renault", model="Clio")
        await create_vehicle(client, other_user, brand="Peugeot", model="208")
        body = (await client.get(f"{API}/vehicles", headers=user.headers)).json()
        assert [v["id"] for v in body["data"]] == [mine["id"]]
        assert body["meta"] == {"page": 1, "limit": 20, "total": 1, "total_pages": 1}

    async def test_search_sort_and_pagination(
        self, client: AsyncClient, user: AuthenticatedUser
    ) -> None:
        for brand, year in (("Renault", 2015), ("Peugeot", 2020), ("Renault", 2022)):
            await create_vehicle(client, user, brand=brand, year=year)
        response = await client.get(
            f"{API}/vehicles",
            headers=user.headers,
            params={"q": "renau", "sort": "-year", "limit": 1, "page": 2},
        )
        body = response.json()
        assert [v["year"] for v in body["data"]] == [2015]
        assert body["meta"] == {"page": 2, "limit": 1, "total": 2, "total_pages": 2}

    async def test_invalid_sort_field(self, client: AsyncClient, user: AuthenticatedUser) -> None:
        response = await client.get(f"{API}/vehicles", headers=user.headers, params={"sort": "vin"})
        assert "sort" in error(response, 422, "VALIDATION_ERROR")["fields"]


class TestAuthorization:
    async def test_strangers_get_404(
        self, client: AsyncClient, user: AuthenticatedUser, other_user: AuthenticatedUser
    ) -> None:
        vehicle = await create_vehicle(client, user)
        url = f"{API}/vehicles/{vehicle['id']}"
        error(await client.get(url, headers=other_user.headers), 404, "NOT_FOUND")
        error(
            await client.patch(url, headers=other_user.headers, json={"color": "red"}),
            404,
            "NOT_FOUND",
        )
        error(await client.delete(url, headers=other_user.headers), 404, "NOT_FOUND")

    async def test_viewer_can_read_but_not_write(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user: AuthenticatedUser,
        other_user: AuthenticatedUser,
    ) -> None:
        vehicle = await create_vehicle(client, user)
        await share_vehicle_in_db(db_session, vehicle["id"], other_user.id, "viewer")
        url = f"{API}/vehicles/{vehicle['id']}"

        assert data(await client.get(url, headers=other_user.headers))["access_role"] == "viewer"
        error(
            await client.patch(url, headers=other_user.headers, json={"color": "red"}),
            403,
            "FORBIDDEN",
        )
        listed = (await client.get(f"{API}/vehicles", headers=other_user.headers)).json()["data"]
        assert [(v["id"], v["access_role"]) for v in listed] == [(vehicle["id"], "viewer")]

    async def test_editor_can_update_but_not_delete(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user: AuthenticatedUser,
        other_user: AuthenticatedUser,
    ) -> None:
        vehicle = await create_vehicle(client, user)
        await share_vehicle_in_db(db_session, vehicle["id"], other_user.id, "editor")
        url = f"{API}/vehicles/{vehicle['id']}"

        assert (
            data(await client.patch(url, headers=other_user.headers, json={"color": "red"}))[
                "color"
            ]
            == "red"
        )
        error(await client.delete(url, headers=other_user.headers), 403, "FORBIDDEN")
        filtered = (
            await client.get(
                f"{API}/vehicles", headers=other_user.headers, params={"role": "owner"}
            )
        ).json()["data"]
        assert filtered == []

    async def test_invalid_vehicle_id(self, client: AsyncClient, user: AuthenticatedUser) -> None:
        response = await client.get(f"{API}/vehicles/not-a-uuid", headers=user.headers)
        assert "vehicle_id" in error(response, 422, "VALIDATION_ERROR")["fields"]


async def test_deleting_the_owner_deletes_vehicles(
    client: AsyncClient,
    user: AuthenticatedUser,
    other_user: AuthenticatedUser,
    db_session: AsyncSession,
) -> None:
    vehicle = await create_vehicle(client, user)
    await share_vehicle_in_db(db_session, vehicle["id"], other_user.id, "viewer")
    await client.request(
        "DELETE", f"{API}/users/me", headers=user.headers, json={"password": user.password}
    )
    error(
        await client.get(f"{API}/vehicles/{vehicle['id']}", headers=other_user.headers),
        404,
        "NOT_FOUND",
    )
