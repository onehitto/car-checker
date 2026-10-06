"""Mileage DTOs."""

import uuid
from datetime import date, datetime

from pydantic import Field

from app.core.schemas import LongText, Mileage, RequestModel, ResponseModel
from app.modules.mileage.models import MileageSource


class MileageCreate(RequestModel):
    mileage: Mileage
    recorded_on: date | None = Field(default=None, description="Reading date; defaults to today.")
    notes: LongText | None = None
    record_history: bool = Field(
        default=True, description="Store the reading in the mileage history."
    )
    force: bool = Field(
        default=False,
        description=(
            "Accept a reading lower than a previous one (odometer replaced or corrected). "
            "The override is audited."
        ),
    )


class MileageEntryResponse(ResponseModel):
    id: uuid.UUID
    vehicle_id: uuid.UUID
    mileage: int
    recorded_on: date
    source: MileageSource
    notes: str | None
    created_by_id: uuid.UUID | None
    created_at: datetime


class MileageUpdateResponse(ResponseModel):
    current_mileage: int
    entry: MileageEntryResponse | None
