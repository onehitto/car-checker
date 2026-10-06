"""Upload validation: size, real content type (magic bytes), extension and file name."""

import re
import unicodedata
from dataclasses import dataclass
from pathlib import PurePosixPath, PureWindowsPath

import filetype

from app.core.exceptions import PayloadTooLargeError, UnsupportedMediaTypeError, ValidationAppError

# Detected MIME type -> accepted file extensions (the first one is canonical).
ALLOWED_TYPES: dict[str, tuple[str, ...]] = {
    "application/pdf": ("pdf",),
    "image/jpeg": ("jpg", "jpeg"),
    "image/png": ("png",),
    "image/webp": ("webp",),
    "image/heic": ("heic", "heif"),
}
IMAGE_TYPES = frozenset(t for t in ALLOWED_TYPES if t.startswith("image/"))
MAX_FILE_NAME_LENGTH = 200
_UNSAFE_CHARACTERS = re.compile(r"[^\w.\- ()]+", re.UNICODE)


@dataclass(frozen=True, slots=True)
class ValidatedFile:
    file_name: str
    content_type: str
    extension: str
    content: bytes

    @property
    def size(self) -> int:
        return len(self.content)


def sanitize_file_name(raw: str | None, extension: str) -> str:
    """Keep a readable, harmless name: no path, no control or special characters."""
    name = PureWindowsPath(PurePosixPath(raw or "").name).name
    name = unicodedata.normalize("NFC", name)
    name = "".join(char for char in name if unicodedata.category(char)[0] != "C")
    stem = name.rsplit(".", 1)[0] if "." in name else name
    stem = _UNSAFE_CHARACTERS.sub("_", stem).strip(" ._")
    stem = stem[: MAX_FILE_NAME_LENGTH - len(extension) - 1] or "file"
    return f"{stem}.{extension}"


def validate_upload(
    content: bytes,
    file_name: str | None,
    max_size: int,
    allowed: frozenset[str] | None = None,
) -> ValidatedFile:
    if not content:
        raise ValidationAppError(fields={"file": "The file is empty."})
    if len(content) > max_size:
        raise PayloadTooLargeError(f"Files are limited to {max_size // (1024 * 1024)} MiB.")

    kind = filetype.guess(content[:8192])
    accepted = allowed if allowed is not None else frozenset(ALLOWED_TYPES)
    if kind is None or kind.mime not in accepted:
        raise UnsupportedMediaTypeError(
            "Unsupported file type. Allowed: " + ", ".join(sorted(accepted))
        )
    extensions = ALLOWED_TYPES[kind.mime]
    declared = PurePosixPath(file_name or "").suffix.lower().lstrip(".")
    if declared and declared not in extensions:
        raise UnsupportedMediaTypeError(
            f"The file extension '.{declared}' does not match its content ({kind.mime})."
        )
    extension = declared or extensions[0]
    return ValidatedFile(sanitize_file_name(file_name, extension), kind.mime, extension, content)
