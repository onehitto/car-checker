from pydantic import BaseModel

from app.core.error_handlers import format_validation_errors
from app.core.exceptions import NotFoundError, RateLimitedError
from app.core.responses import ApiResponse, PaginatedResponse


def test_validation_errors_are_flattened_to_dotted_paths() -> None:
    errors = [
        {"loc": ("body", "mileage"), "msg": "Input should be greater than or equal to 0"},
        {"loc": ("body", "moves", 0, "to_position"), "msg": "Value error, Invalid position"},
        {"loc": ("query", "limit"), "msg": "Input should be less than or equal to 100"},
        {"loc": ("body", "mileage"), "msg": "second message is ignored"},
    ]
    assert format_validation_errors(errors) == {
        "mileage": "Input should be greater than or equal to 0",
        "moves.0.to_position": "Invalid position",
        "limit": "Input should be less than or equal to 100",
    }


def test_body_level_error_uses_root_key() -> None:
    assert format_validation_errors([{"loc": ("body",), "msg": "Field required"}]) == {
        "__root__": "Field required"
    }


def test_not_found_error_message_mentions_resource() -> None:
    assert NotFoundError("Vehicle").message == "Vehicle not found."


def test_rate_limited_error_sets_retry_after_header() -> None:
    assert RateLimitedError(retry_after=12).headers == {"Retry-After": "12"}


class Item(BaseModel):
    name: str


def test_envelopes_serialize_consistently() -> None:
    assert ApiResponse[Item](data=Item(name="a")).model_dump() == {
        "success": True,
        "data": {"name": "a"},
    }
    page = PaginatedResponse[Item](
        data=[Item(name="a")], meta={"page": 1, "limit": 20, "total": 1, "total_pages": 1}
    )
    assert page.model_dump()["meta"]["total_pages"] == 1
