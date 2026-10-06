from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.core.exceptions import PayloadTooLargeError, UnsupportedMediaTypeError, ValidationAppError
from app.modules.attachments.storage import LocalStorageBackend, StorageKeyError
from app.modules.attachments.validation import IMAGE_TYPES, sanitize_file_name, validate_upload

PDF = b"%PDF-1.7\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"
PNG = bytes.fromhex("89504e470d0a1a0a0000000d49484452") + b"\x00" * 32


class TestValidation:
    def test_accepts_pdf_and_detects_type_from_content(self) -> None:
        validated = validate_upload(PDF, "Facture Mars.pdf", max_size=1024)
        assert (validated.content_type, validated.extension, validated.file_name) == (
            "application/pdf",
            "pdf",
            "Facture Mars.pdf",
        )

    def test_missing_extension_gets_the_canonical_one(self) -> None:
        assert validate_upload(PNG, "photo", max_size=1024).file_name == "photo.png"

    def test_rejects_disguised_files(self) -> None:
        with pytest.raises(UnsupportedMediaTypeError, match="does not match"):
            validate_upload(PNG, "invoice.pdf", max_size=1024)
        with pytest.raises(UnsupportedMediaTypeError, match="Unsupported"):
            validate_upload(b"#!/bin/sh\nrm -rf /\n", "script.pdf", max_size=1024)

    def test_size_limits(self) -> None:
        with pytest.raises(PayloadTooLargeError):
            validate_upload(PDF, "a.pdf", max_size=10)
        with pytest.raises(ValidationAppError):
            validate_upload(b"", "a.pdf", max_size=10)

    def test_images_only(self) -> None:
        with pytest.raises(UnsupportedMediaTypeError):
            validate_upload(PDF, "a.pdf", max_size=1024, allowed=IMAGE_TYPES)

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("../../etc/passwd.pdf", "passwd.pdf"),
            ("C:\\Users\\x\\scan.pdf", "scan.pdf"),
            ("<script>.pdf", "script.pdf"),
            ("contrat\x00assurance.pdf", "contratassurance.pdf"),
            ("", "file.pdf"),
            ("é" * 300 + ".pdf", "é" * 196 + ".pdf"),
        ],
    )
    def test_sanitize(self, raw: str, expected: str) -> None:
        assert sanitize_file_name(raw, "pdf") == expected


class TestLocalStorage:
    async def test_round_trip_and_listing(self, tmp_path: Path) -> None:
        storage = LocalStorageBackend(tmp_path)
        await storage.save("v1/2026/10/a.pdf", PDF)
        assert await storage.exists("v1/2026/10/a.pdf")
        assert b"".join([chunk async for chunk in storage.open("v1/2026/10/a.pdf")]) == PDF
        future = datetime.now(UTC) + timedelta(minutes=1)
        assert [key async for key in storage.list_keys(future)] == ["v1/2026/10/a.pdf"]
        await storage.delete("v1/2026/10/a.pdf")
        assert not await storage.exists("v1/2026/10/a.pdf")

    async def test_keys_cannot_escape_the_root(self, tmp_path: Path) -> None:
        storage = LocalStorageBackend(tmp_path / "uploads")
        with pytest.raises(StorageKeyError):
            await storage.save("../outside.pdf", PDF)
