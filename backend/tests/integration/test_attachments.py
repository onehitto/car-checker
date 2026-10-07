"""File attachments and vehicle picture."""

import os
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.clock import FixedClock
from app.core.config import Settings
from app.jobs.registry import JobContext
from app.jobs.tasks import cleanup_orphan_files
from app.modules.attachments.storage import LocalStorageBackend
from tests.helpers import API, AuthenticatedUser, create_maintenance, create_vehicle, data, error

PDF = b"%PDF-1.7\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"
PNG = bytes.fromhex("89504e470d0a1a0a0000000d49484452") + b"\x00" * 32


@pytest.fixture
async def vehicle(client: AsyncClient, user: AuthenticatedUser) -> dict[str, Any]:
    return await create_vehicle(client, user)


def url(vehicle: dict[str, Any]) -> str:
    return f"{API}/vehicles/{vehicle['id']}/attachments"


async def upload(
    client: AsyncClient,
    user: AuthenticatedUser,
    vehicle: dict[str, Any],
    *,
    content: bytes = PDF,
    name: str = "invoice.pdf",
    **form: str,
) -> Any:
    return await client.post(
        url(vehicle),
        headers=user.headers,
        files={"file": (name, content, "application/octet-stream")},
        data=form,
    )


def storage_root(app: FastAPI) -> Path:
    storage = app.state.storage
    assert isinstance(storage, LocalStorageBackend)
    return storage.root


async def test_upload_download_and_delete(
    client: AsyncClient, app: FastAPI, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    record = await create_maintenance(client, user, vehicle["id"])
    attachment = data(
        await upload(
            client,
            user,
            vehicle,
            name="../Facture garage.pdf",
            entity_type="maintenance_record",
            entity_id=record["id"],
        ),
        201,
    )
    assert (attachment["file_name"], attachment["content_type"], attachment["file_size"]) == (
        "Facture garage.pdf",
        "application/pdf",
        len(PDF),
    )
    stored = list(storage_root(app).rglob("*.pdf"))
    assert len(stored) == 1 and vehicle["id"] in str(stored[0])

    download = await client.get(f"{url(vehicle)}/{attachment['id']}/download", headers=user.headers)
    assert download.status_code == 200
    assert download.content == PDF
    assert download.headers["content-type"] == "application/pdf"
    assert (
        download.headers["content-disposition"]
        == "attachment; filename*=UTF-8''Facture%20garage.pdf"
    )

    listed = (
        await client.get(url(vehicle), headers=user.headers, params={"entity_id": record["id"]})
    ).json()
    assert listed["meta"]["total"] == 1

    assert (
        await client.delete(f"{url(vehicle)}/{attachment['id']}", headers=user.headers)
    ).status_code == 204
    assert list(storage_root(app).rglob("*.pdf")) == []


async def test_upload_validation(
    client: AsyncClient, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    error(
        await upload(
            client, user, vehicle, content=b"MZ\x90\x00binary", name="a.pdf", entity_type="vehicle"
        ),
        415,
        "UNSUPPORTED_MEDIA_TYPE",
    )
    error(
        await upload(client, user, vehicle, content=PNG, name="a.pdf", entity_type="vehicle"),
        415,
        "UNSUPPORTED_MEDIA_TYPE",
    )
    missing = await upload(client, user, vehicle, entity_type="expense")
    assert "entity_id" in error(missing, 422, "VALIDATION_ERROR")["fields"]
    other_vehicle = await create_vehicle(client, user)
    foreign_record = await create_maintenance(client, user, other_vehicle["id"])
    wrong = await upload(
        client, user, vehicle, entity_type="maintenance_record", entity_id=foreign_record["id"]
    )
    assert "entity_id" in error(wrong, 422, "VALIDATION_ERROR")["fields"]


async def test_upload_size_limit(
    app_factory: Any, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    from httpx import ASGITransport

    small = app_factory(max_upload_size=2048)
    async with AsyncClient(transport=ASGITransport(app=small), base_url="http://test") as c:
        response = await c.post(
            url(vehicle),
            headers=user.headers,
            files={"file": ("big.pdf", PDF + b"0" * 4096, "application/pdf")},
            data={"entity_type": "vehicle"},
        )
        error(response, 413, "PAYLOAD_TOO_LARGE")
        huge = await c.post(
            url(vehicle),
            headers=user.headers,
            files={"file": ("huge.pdf", PDF + b"0" * (2 * 1024 * 1024), "application/pdf")},
            data={"entity_type": "vehicle"},
        )
        error(huge, 413, "PAYLOAD_TOO_LARGE")


async def test_vehicle_image(
    client: AsyncClient, app: FastAPI, user: AuthenticatedUser, vehicle: dict[str, Any]
) -> None:
    image_url = f"{API}/vehicles/{vehicle['id']}/image"
    first = data(
        await client.put(
            image_url, headers=user.headers, files={"file": ("car.png", PNG, "image/png")}
        )
    )
    assert (
        data(await client.get(f"{API}/vehicles/{vehicle['id']}", headers=user.headers))[
            "image_attachment_id"
        ]
        == first["id"]
    )

    second = data(
        await client.put(
            image_url, headers=user.headers, files={"file": ("car2.png", PNG, "image/png")}
        )
    )
    assert len(list(storage_root(app).rglob("*.png"))) == 1
    error(await client.get(f"{url(vehicle)}/{first['id']}", headers=user.headers), 404, "NOT_FOUND")

    pdf = await client.put(
        image_url, headers=user.headers, files={"file": ("car.pdf", PDF, "application/pdf")}
    )
    error(pdf, 415, "UNSUPPORTED_MEDIA_TYPE")

    assert (await client.delete(image_url, headers=user.headers)).status_code == 204
    assert (
        data(await client.get(f"{API}/vehicles/{vehicle['id']}", headers=user.headers))[
            "image_attachment_id"
        ]
        is None
    )
    error(
        await client.get(f"{url(vehicle)}/{second['id']}", headers=user.headers), 404, "NOT_FOUND"
    )


async def test_deleting_vehicle_removes_files_and_viewer_cannot_upload(
    client: AsyncClient,
    app: FastAPI,
    db_session: AsyncSession,
    user: AuthenticatedUser,
    other_user: AuthenticatedUser,
    vehicle: dict[str, Any],
) -> None:
    from tests.helpers import share_vehicle_in_db

    await share_vehicle_in_db(db_session, vehicle["id"], other_user.id, "viewer")
    error(await upload(client, other_user, vehicle, entity_type="vehicle"), 403, "FORBIDDEN")

    data(await upload(client, user, vehicle, entity_type="vehicle"), 201)
    assert len(list(storage_root(app).rglob("*.pdf"))) == 1
    await client.delete(f"{API}/vehicles/{vehicle['id']}", headers=user.headers)
    assert list(storage_root(app).rglob("*.pdf")) == []


async def test_cleanup_job_removes_orphans(
    client: AsyncClient,
    app: FastAPI,
    user: AuthenticatedUser,
    vehicle: dict[str, Any],
    session_factory: async_sessionmaker[AsyncSession],
    clock: FixedClock,
    settings: Settings,
) -> None:
    record = await create_maintenance(client, user, vehicle["id"])
    data(
        await upload(
            client, user, vehicle, entity_type="maintenance_record", entity_id=record["id"]
        ),
        201,
    )
    kept = data(await upload(client, user, vehicle, entity_type="vehicle"), 201)
    await client.delete(
        f"{API}/vehicles/{vehicle['id']}/maintenance/{record['id']}", headers=user.headers
    )
    stray = storage_root(app) / "stray" / "lost.pdf"
    stray.parent.mkdir(parents=True)
    stray.write_bytes(PDF)
    os.utime(stray, (946_684_800, 946_684_800))  # an old file, outside the grace period

    ctx = JobContext(
        session_factory=session_factory,
        clock=clock,
        settings=settings,
        extras={"storage": app.state.storage},
    )
    result = await cleanup_orphan_files(ctx)
    assert result == {"orphan_attachments": 1, "stray_files": 1, "detached_notes": 0}
    remaining = data(await client.get(url(vehicle), headers=user.headers))
    assert [a["id"] for a in remaining] == [kept["id"]]
    assert len(list(storage_root(app).rglob("*.pdf"))) == 1
