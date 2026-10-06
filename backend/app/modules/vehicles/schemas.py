"""Vehicle DTOs."""

import re
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Self

from pydantic import AfterValidator, Field, StringConstraints, model_validator

from app.core.schemas import CurrencyCode, LongText, Mileage, Money, RequestModel, ResponseModel
from app.modules.vehicles.models import FuelType, TransmissionType, VehicleRole, VehicleStatus

MIN_VEHICLE_YEAR = 1886
_VIN_PATTERN = re.compile(r"^[A-Z0-9]{5,32}$")


def _validate_vin(value: str) -> str:
    vin = value.replace(" ", "").replace("-", "").upper()
    if not _VIN_PATTERN.fullmatch(vin):
        raise ValueError("VIN must contain 5 to 32 letters or digits.")
    if len(vin) == 17 and set(vin) & {"I", "O", "Q"}:
        raise ValueError("A 17-character VIN cannot contain the letters I, O or Q.")
    return vin


def _normalize_plate(value: str) -> str:
    return " ".join(value.upper().split())


Vin = Annotated[str, AfterValidator(_validate_vin), Field(examples=["UU1LSDAAH12345678"])]
LicensePlate = Annotated[
    str,
    StringConstraints(min_length=1, max_length=20),
    AfterValidator(_normalize_plate),
    Field(examples=["12345-A-6"]),
]
Label = Annotated[str, StringConstraints(min_length=1, max_length=64)]
VehicleYear = Annotated[int, Field(ge=MIN_VEHICLE_YEAR, le=2100, examples=[2019])]


class VehicleBase(RequestModel):
    nickname: Annotated[str, StringConstraints(min_length=1, max_length=100)] | None = None
    trim: Label | None = None
    license_plate: LicensePlate | None = None
    vin: Vin | None = None
    transmission_type: TransmissionType | None = None
    engine: Label | None = Field(default=None, examples=["1.5 dCi"])
    engine_displacement_cc: int | None = Field(default=None, gt=0, le=20_000, examples=[1461])
    horsepower: int | None = Field(default=None, gt=0, le=3_000, examples=[90])
    color: Annotated[str, StringConstraints(min_length=1, max_length=32)] | None = None
    purchase_date: date | None = None
    purchase_price: Money | None = None
    notes: LongText | None = None


class VehicleCreate(VehicleBase):
    brand: Label = Field(examples=["Dacia"])
    model: Label = Field(examples=["Logan"])
    year: VehicleYear
    fuel_type: FuelType
    currency: CurrencyCode | None = Field(
        default=None, description="Defaults to the owner's preferred currency."
    )
    initial_mileage: Mileage = Field(default=0, description="Odometer when acquired (km).")
    current_mileage: Mileage | None = Field(
        default=None, description="Current odometer (km); defaults to initial_mileage."
    )
    status: VehicleStatus = VehicleStatus.ACTIVE

    @model_validator(mode="after")
    def _current_not_below_initial(self) -> Self:
        if self.current_mileage is not None and self.current_mileage < self.initial_mileage:
            raise ValueError("current_mileage cannot be lower than initial_mileage.")
        return self


class VehicleUpdate(VehicleBase):
    """Partial update. The odometer is updated through the mileage endpoint."""

    brand: Label | None = None
    model: Label | None = None
    year: VehicleYear | None = None
    fuel_type: FuelType | None = None
    currency: CurrencyCode | None = None
    initial_mileage: Mileage | None = None
    status: VehicleStatus | None = None


class VehicleResponse(ResponseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    nickname: str | None
    display_name: str
    brand: str
    model: str
    trim: str | None
    year: int
    license_plate: str | None
    vin: str | None
    fuel_type: FuelType
    transmission_type: TransmissionType | None
    engine: str | None
    engine_displacement_cc: int | None
    horsepower: int | None
    color: str | None
    purchase_date: date | None
    purchase_price: Decimal | None
    currency: str
    initial_mileage: int
    current_mileage: int
    status: VehicleStatus
    image_attachment_id: uuid.UUID | None = Field(
        description="Download with /vehicles/{id}/attachments/{image_attachment_id}/download."
    )
    notes: str | None
    access_role: VehicleRole | None = Field(
        default=None, description="Role of the caller on this vehicle."
    )
    created_at: datetime
    updated_at: datetime


class VehicleSummary(ResponseModel):
    """Compact vehicle representation embedded in other resources."""

    id: uuid.UUID
    display_name: str
    brand: str
    model: str
    year: int
    license_plate: str | None
    current_mileage: int
    currency: str
    status: VehicleStatus
