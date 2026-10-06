"""Shared Pydantic base classes and constrained field types used by module schemas."""

from datetime import date, timedelta
from decimal import Decimal
from typing import Annotated
from zoneinfo import available_timezones

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StringConstraints,
)

from app.core.exceptions import ValidationAppError


class RequestModel(BaseModel):
    """Request bodies: unknown fields are rejected, strings are trimmed."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ResponseModel(BaseModel):
    """Response bodies: built from ORM objects."""

    model_config = ConfigDict(from_attributes=True)


_TIMEZONES = frozenset(available_timezones())


def _validate_timezone(value: str) -> str:
    if value not in _TIMEZONES:
        raise ValueError("Unknown time zone; use an IANA name such as 'Africa/Casablanca'.")
    return value


def _upper(value: object) -> object:
    return value.upper() if isinstance(value, str) else value


MAX_MILEAGE = 2_000_000
MAX_MONEY = Decimal("9999999999.99")

Mileage = Annotated[int, Field(ge=0, le=MAX_MILEAGE, description="Distance in kilometres.")]
Money = Annotated[
    Decimal,
    Field(ge=0, le=MAX_MONEY, max_digits=12, decimal_places=2, examples=["79.95"]),
]
UnitPrice = Annotated[Decimal, Field(ge=0, max_digits=10, decimal_places=4, examples=["1.8900"])]
CurrencyCode = Annotated[
    str,
    BeforeValidator(_upper),
    StringConstraints(pattern=r"^[A-Z]{3}$"),
    Field(description="ISO 4217 currency code.", examples=["EUR", "MAD"]),
]
TimezoneName = Annotated[
    str, AfterValidator(_validate_timezone), Field(examples=["Africa/Casablanca"])
]
PhoneNumber = Annotated[
    str, StringConstraints(pattern=r"^\+?[0-9 ().\-]{6,32}$"), Field(examples=["+212600000000"])
]
PersonName = Annotated[str, StringConstraints(min_length=1, max_length=100)]
ShortText = Annotated[str, StringConstraints(min_length=1, max_length=200)]
LongText = Annotated[str, StringConstraints(max_length=10_000)]


def ensure_not_future(value: date | None, today: date, field: str) -> None:
    """Factual dates (services, fill-ups, readings) cannot be in the future.

    One day of tolerance absorbs time-zone differences between client and server.
    """
    if value is not None and value > today + timedelta(days=1):
        raise ValidationAppError(fields={field: "Date cannot be in the future."})


class MessageResponse(BaseModel):
    message: str
