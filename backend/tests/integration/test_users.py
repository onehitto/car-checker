"""Profile, sessions and account deletion."""

from httpx import AsyncClient

from tests.helpers import API, AuthenticatedUser, data, error, login


async def test_get_profile(client: AsyncClient, user: AuthenticatedUser) -> None:
    profile = data(await client.get(f"{API}/users/me", headers=user.headers))
    assert profile["id"] == user.id
    assert profile["email"] == user.email
    assert profile["preferred_distance_unit"] == "km"
    assert "password_hash" not in profile


async def test_profile_requires_authentication(client: AsyncClient) -> None:
    error(await client.get(f"{API}/users/me"), 401, "AUTHENTICATION_REQUIRED")


async def test_partial_update(client: AsyncClient, user: AuthenticatedUser) -> None:
    updated = data(
        await client.patch(
            f"{API}/users/me",
            headers=user.headers,
            json={
                "first_name": "Amina",
                "preferred_language": "ar",
                "preferred_distance_unit": "mi",
                "preferred_consumption_unit": "mpg_us",
                "preferred_currency": "usd",
                "phone_number": "+212 600-000000",
                "timezone": "Africa/Casablanca",
            },
        )
    )
    assert updated["first_name"] == "Amina"
    assert updated["last_name"] == "User"
    assert updated["preferred_language"] == "ar"
    assert updated["preferred_currency"] == "USD"
    assert updated["timezone"] == "Africa/Casablanca"

    cleared = data(
        await client.patch(f"{API}/users/me", headers=user.headers, json={"phone_number": None})
    )
    assert cleared["phone_number"] is None


async def test_update_rejects_null_required_fields_and_unknown_fields(
    client: AsyncClient, user: AuthenticatedUser
) -> None:
    response = await client.patch(f"{API}/users/me", headers=user.headers, json={"last_name": None})
    assert error(response, 422, "VALIDATION_ERROR")["fields"] == {
        "last_name": "This field cannot be null."
    }
    response = await client.patch(f"{API}/users/me", headers=user.headers, json={"email": "x@y.z"})
    assert "email" in error(response, 422, "VALIDATION_ERROR")["fields"]


async def test_sessions_list_and_revoke(client: AsyncClient, user: AuthenticatedUser) -> None:
    second = await login(client, user.email)
    sessions = data(await client.get(f"{API}/users/me/sessions", headers=user.headers))
    assert len(sessions) == 2
    current = [s for s in sessions if s["current"]]
    assert len(current) == 1
    assert current[0]["ip_address"] == "127.0.0.1"

    other_id = next(s["id"] for s in sessions if not s["current"])
    response = await client.delete(f"{API}/users/me/sessions/{other_id}", headers=user.headers)
    assert response.status_code == 204
    error(
        await client.get(f"{API}/users/me", headers=second.headers), 401, "AUTHENTICATION_REQUIRED"
    )

    response = await client.delete(f"{API}/users/me/sessions/{other_id}", headers=user.headers)
    error(response, 404, "NOT_FOUND")


async def test_cannot_revoke_someone_elses_session(
    client: AsyncClient, user: AuthenticatedUser, other_user: AuthenticatedUser
) -> None:
    sessions = data(await client.get(f"{API}/users/me/sessions", headers=other_user.headers))
    response = await client.delete(
        f"{API}/users/me/sessions/{sessions[0]['id']}", headers=user.headers
    )
    error(response, 404, "NOT_FOUND")
    assert (await client.get(f"{API}/users/me", headers=other_user.headers)).status_code == 200


async def test_delete_account_requires_password(
    client: AsyncClient, user: AuthenticatedUser
) -> None:
    response = await client.request(
        "DELETE", f"{API}/users/me", headers=user.headers, json={"password": "Wrong-pass1"}
    )
    assert "password" in error(response, 422, "VALIDATION_ERROR")["fields"]

    response = await client.request(
        "DELETE", f"{API}/users/me", headers=user.headers, json={"password": user.password}
    )
    assert response.status_code == 204
    error(await client.get(f"{API}/users/me", headers=user.headers), 401, "AUTHENTICATION_REQUIRED")
    error(
        await client.post(
            f"{API}/auth/login", json={"email": user.email, "password": user.password}
        ),
        401,
        "INVALID_CREDENTIALS",
    )
