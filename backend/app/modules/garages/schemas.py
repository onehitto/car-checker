"""Garage DTOs."""

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import EmailStr, Field, StringConstraints

from app.core.schemas import LongText, PhoneNumber, RequestModel, ResponseModel
from app.modules.garages.models import GarageType

GarageName = Annotated[str, StringConstraints(min_length=1, max_length=120)]
Text100 = Annotated[str, StringConstraints(min_length=1, max_length=100)]
Website = Annotated[
    str,
    StringConstraints(max_length=255, pattern=r"^https?://[^\s]+$"),
    Field(examples=["https://garage.example.com"]),
]


class GarageBase(RequestModel):
    garage_type: GarageType | None = None
    contact_name: GarageName | None = None
    phone: PhoneNumber | None = None
    email: EmailStr | None = None
    address: Annotated[str, StringConstraints(min_length=1, max_length=255)] | None = None
    city: Text100 | None = None
    country: Text100 | None = None
    website: Website | None = None
    notes: LongText | None = None


class GarageCreate(GarageBase):
    name: GarageName
    garage_type: GarageType = GarageType.GARAGE


class GarageUpdate(GarageBase):
    name: GarageName | None = None


class GarageResponse(ResponseModel):
    id: uuid.UUID
    name: str
    garage_type: GarageType
    contact_name: str | None
    phone: str | None
    email: str | None
    address: str | None
    city: str | None
    country: str | None
    website: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class GarageSummary(ResponseModel):
    """Garage embedded in maintenance records and part replacements."""

    id: uuid.UUID
    name: str
    garage_type: GarageType
    city: str | None
    phone: str | None
