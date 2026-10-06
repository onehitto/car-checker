"""User DTOs."""

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BeforeValidator, Field

from app.core.i18n import Language
from app.core.schemas import (
    CurrencyCode,
    PersonName,
    PhoneNumber,
    RequestModel,
    ResponseModel,
    TimezoneName,
)
from app.core.units import ConsumptionUnit, DistanceUnit
from app.modules.users.models import UserRole


class UserResponse(ResponseModel):
    id: uuid.UUID
    email: str
    first_name: str
    last_name: str
    phone_number: str | None
    preferred_language: Language
    preferred_currency: str
    preferred_distance_unit: DistanceUnit
    preferred_consumption_unit: ConsumptionUnit
    timezone: str
    role: UserRole
    email_verified_at: datetime | None
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime


class UserUpdate(RequestModel):
    """Partial profile update; only provided fields change. `phone_number` may be null."""

    first_name: PersonName | None = None
    last_name: PersonName | None = None
    phone_number: PhoneNumber | None = None
    preferred_language: Language | None = None
    preferred_currency: CurrencyCode | None = None
    preferred_distance_unit: DistanceUnit | None = None
    preferred_consumption_unit: ConsumptionUnit | None = None
    timezone: TimezoneName | None = None


class DeleteAccountRequest(RequestModel):
    password: str = Field(min_length=1, max_length=128, description="Current password.")


def _ip_to_str(value: object) -> object:
    # asyncpg returns INET values as ipaddress objects.
    return None if value is None else str(value)


class SessionResponse(ResponseModel):
    id: uuid.UUID
    user_agent: str | None
    ip_address: Annotated[str | None, BeforeValidator(_ip_to_str)]
    created_at: datetime
    last_used_at: datetime
    expires_at: datetime
    current: bool = Field(description="True for the session making this request.")
