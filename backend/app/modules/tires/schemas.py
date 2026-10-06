"""Tire DTOs."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal, Self

from pydantic import Field, StringConstraints, model_validator

from app.core.schemas import LongText, Mileage, Money, RequestModel, ResponseModel
from app.modules.tires.models import (
    TireCondition,
    TireEventType,
    TirePosition,
    TireSeason,
    TireStatus,
)

TireText = Annotated[str, StringConstraints(min_length=1, max_length=80)]
TreadDepth = Annotated[Decimal, Field(ge=0, le=30, max_digits=4, decimal_places=1)]
TireSize = Annotated[
    str, StringConstraints(min_length=3, max_length=32), Field(examples=["205/55 R16 91V"])
]


class TireFields(RequestModel):
    model: TireText | None = None
    dot_code: Annotated[str, StringConstraints(min_length=1, max_length=20)] | None = None
    condition: TireCondition | None = None
    purchase_date: date | None = None
    price: Money | None = None
    tread_depth_mm: TreadDepth | None = None
    pressure_notes: Annotated[str, StringConstraints(max_length=200)] | None = None
    notes: LongText | None = None


class TireCreate(TireFields):
    """A tire with a `position` is mounted (an `installed` event is recorded), else stored."""

    brand: TireText
    size: TireSize
    season: TireSeason
    position: TirePosition | None = None
    installed_date: date | None = Field(default=None, description="Defaults to today if mounted.")
    installed_mileage: Mileage | None = None


class TireUpdate(TireFields):
    """Descriptive fields; position and status change through events and rotations."""

    brand: TireText | None = None
    size: TireSize | None = None
    season: TireSeason | None = None


class TireResponse(ResponseModel):
    id: uuid.UUID
    vehicle_id: uuid.UUID
    brand: str
    model: str | None
    size: str
    season: TireSeason
    dot_code: str | None
    position: TirePosition | None
    status: TireStatus
    condition: TireCondition | None
    purchase_date: date | None
    price: Decimal | None
    installed_date: date | None
    installed_mileage: int | None
    tread_depth_mm: Decimal | None
    pressure_notes: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class TireEventCreate(RequestModel):
    event_type: Literal["installed", "removed", "inspected", "repaired", "discarded"] = Field(
        description="Rotations go through the rotations endpoint."
    )
    event_date: date
    mileage: Mileage | None = None
    to_position: TirePosition | None = Field(
        default=None, description="Required to install (mount) the tire."
    )
    tread_depth_mm: TreadDepth | None = None
    condition: TireCondition | None = None
    notes: LongText | None = None

    @model_validator(mode="after")
    def _position_for_installation(self) -> Self:
        if self.event_type == "installed" and self.to_position is None:
            raise ValueError("to_position is required to install a tire.")
        return self


class TireEventResponse(ResponseModel):
    id: uuid.UUID
    tire_id: uuid.UUID
    vehicle_id: uuid.UUID
    event_type: TireEventType
    event_date: date
    mileage: int | None
    from_position: TirePosition | None
    to_position: TirePosition | None
    tread_depth_mm: Decimal | None
    notes: str | None
    created_at: datetime


class TireMove(RequestModel):
    tire_id: uuid.UUID
    to_position: TirePosition


class TireRotation(RequestModel):
    rotation_date: date
    mileage: Mileage | None = None
    moves: list[TireMove] = Field(min_length=1, max_length=5)
    notes: LongText | None = None

    @model_validator(mode="after")
    def _unique_moves(self) -> Self:
        if len({move.tire_id for move in self.moves}) != len(self.moves):
            raise ValueError("Each tire can only be moved once per rotation.")
        if len({move.to_position for move in self.moves}) != len(self.moves):
            raise ValueError("Two tires cannot be moved to the same position.")
        return self
