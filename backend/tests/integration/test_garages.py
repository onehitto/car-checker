"""Garages are private to their owner."""

from httpx import AsyncClient

from tests.helpers import API, AuthenticatedUser, create_garage, data, error


async def test_crud(client: AsyncClient, user: AuthenticatedUser) -> None:
    garage = await create_garage(
        client,
        user,
        garage_type="dealership",
        phone="+212 522 000 000",
        email="Contact@Atlas.ma",
        website="https://atlas.example.ma",
    )
    assert garage["garage_type"] == "dealership"
    url = f"{API}/garages/{garage['id']}"

    assert data(await client.get(url, headers=user.headers))["name"] == "Garage Atlas"
    updated = data(
        await client.patch(url, headers=user.headers, json={"city": "Rabat", "phone": None})
    )
    assert (updated["city"], updated["phone"]) == ("Rabat", None)

    assert (await client.delete(url, headers=user.headers)).status_code == 204
    error(await client.get(url, headers=user.headers), 404, "NOT_FOUND")


async def test_validation(client: AsyncClient, user: AuthenticatedUser) -> None:
    response = await client.post(
        f"{API}/garages",
        headers=user.headers,
        json={"name": "", "website": "javascript:alert(1)", "email": "nope"},
    )
    assert set(error(response, 422, "VALIDATION_ERROR")["fields"]) == {"name", "website", "email"}


async def test_list_filters_and_isolation(
    client: AsyncClient, user: AuthenticatedUser, other_user: AuthenticatedUser
) -> None:
    await create_garage(client, user, name="Pneus Express", garage_type="tire_shop", city="Fes")
    await create_garage(client, user, name="Garage Atlas", city="Casablanca")
    foreign = await create_garage(client, other_user, name="Hidden")

    body = (await client.get(f"{API}/garages", headers=user.headers)).json()
    assert [g["name"] for g in body["data"]] == ["Garage Atlas", "Pneus Express"]

    tire_shops = (
        await client.get(
            f"{API}/garages", headers=user.headers, params={"garage_type": "tire_shop"}
        )
    ).json()["data"]
    assert [g["name"] for g in tire_shops] == ["Pneus Express"]

    searched = (
        await client.get(f"{API}/garages", headers=user.headers, params={"q": "casa"})
    ).json()["data"]
    assert [g["name"] for g in searched] == ["Garage Atlas"]

    error(
        await client.get(f"{API}/garages/{foreign['id']}", headers=user.headers), 404, "NOT_FOUND"
    )
    error(
        await client.delete(f"{API}/garages/{foreign['id']}", headers=user.headers),
        404,
        "NOT_FOUND",
    )
