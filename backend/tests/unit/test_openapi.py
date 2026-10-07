"""Contract checks on the generated OpenAPI document."""

from typing import Any

import pytest

from app.api.openapi import OPENAPI_TAGS
from app.core.config import Settings
from app.main import create_app

PUBLIC = {
    ("post", "/api/v1/auth/register"),
    ("post", "/api/v1/auth/login"),
    ("post", "/api/v1/auth/refresh"),
    ("post", "/api/v1/auth/password/forgot"),
    ("post", "/api/v1/auth/password/reset"),
    ("get", "/health"),
    ("get", "/api/v1/health"),
}


@pytest.fixture(scope="module")
def operations() -> list[tuple[str, str, dict[str, Any]]]:
    spec = create_app(Settings(_env_file=None)).openapi()  # type: ignore[call-arg]
    return [
        (method, path, operation)
        for path, item in spec["paths"].items()
        for method, operation in item.items()
    ]


def test_every_private_operation_requires_a_bearer_token(
    operations: list[tuple[str, str, dict[str, Any]]],
) -> None:
    unsecured = {(m, p) for m, p, op in operations if "security" not in op}
    assert unsecured == PUBLIC
    for method, path, operation in operations:
        if (method, path) not in PUBLIC:
            assert "401" in operation["responses"], (method, path)


def test_errors_use_the_error_envelope(operations: list[tuple[str, str, dict[str, Any]]]) -> None:
    for method, path, operation in operations:
        for status, response in operation["responses"].items():
            if status.startswith(("4", "5")):
                schema = response["content"]["application/json"]["schema"]["$ref"]
                assert schema.endswith("/ErrorResponse"), (method, path, status)


def test_operations_are_documented_and_tagged(
    operations: list[tuple[str, str, dict[str, Any]]],
) -> None:
    known_tags = {tag["name"] for tag in OPENAPI_TAGS}
    for method, path, operation in operations:
        assert operation.get("summary"), (method, path)
        assert set(operation["tags"]) <= known_tags, (method, path)
