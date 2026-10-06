"""Helpers for PATCH semantics: only fields present in the request are changed."""

from collections.abc import Collection
from typing import Any

from pydantic import BaseModel

from app.core.exceptions import ValidationAppError


def apply_updates(
    target: object, data: BaseModel, *, required: Collection[str] = ()
) -> dict[str, Any]:
    """Copy the fields explicitly sent by the client onto `target`.

    Fields listed in `required` cannot be cleared with null. Returns the applied changes.
    """
    changes = data.model_dump(exclude_unset=True)
    null_fields = {
        name: "This field cannot be null."
        for name, value in changes.items()
        if value is None and name in required
    }
    if null_fields:
        raise ValidationAppError(fields=null_fields)
    for name, value in changes.items():
        setattr(target, name, value)
    return changes
