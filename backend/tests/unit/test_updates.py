from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from app.core.exceptions import ValidationAppError
from app.core.updates import apply_updates


class Patch(BaseModel):
    name: str | None = None
    note: str | None = None


def test_only_sent_fields_are_applied() -> None:
    target = SimpleNamespace(name="old", note="keep")
    changes = apply_updates(target, Patch.model_validate({"name": "new"}), required={"name"})
    assert changes == {"name": "new"}
    assert (target.name, target.note) == ("new", "keep")


def test_optional_fields_can_be_cleared() -> None:
    target = SimpleNamespace(name="old", note="x")
    apply_updates(target, Patch.model_validate({"note": None}), required={"name"})
    assert target.note is None


def test_required_fields_cannot_be_cleared() -> None:
    target = SimpleNamespace(name="old", note="x")
    with pytest.raises(ValidationAppError) as exc_info:
        apply_updates(target, Patch.model_validate({"name": None}), required={"name"})
    assert exc_info.value.fields == {"name": "This field cannot be null."}
    assert target.name == "old"
