"""Authentication DTOs."""

from pydantic import EmailStr, Field, ValidationInfo, field_validator

from app.core.i18n import Language
from app.core.schemas import (
    CurrencyCode,
    PersonName,
    PhoneNumber,
    RequestModel,
    ResponseModel,
    TimezoneName,
)
from app.core.security import PASSWORD_MAX_LENGTH, password_policy_violation
from app.core.units import ConsumptionUnit, DistanceUnit
from app.modules.users.schemas import UserResponse

_OPAQUE_TOKEN = Field(min_length=20, max_length=200)


def _normalize_email(value: str) -> str:
    return value.strip().lower()


class RegisterRequest(RequestModel):
    email: EmailStr
    password: str = Field(
        max_length=PASSWORD_MAX_LENGTH,
        description="8-128 characters, at least one letter and one digit.",
        examples=["S3cure-pass"],
    )
    first_name: PersonName
    last_name: PersonName
    phone_number: PhoneNumber | None = None
    preferred_language: Language = Language.EN
    preferred_currency: CurrencyCode = "EUR"
    preferred_distance_unit: DistanceUnit = DistanceUnit.KM
    preferred_consumption_unit: ConsumptionUnit = ConsumptionUnit.L_100KM
    timezone: TimezoneName = "UTC"

    _lower_email = field_validator("email")(_normalize_email)

    @field_validator("password")
    @classmethod
    def _password_policy(cls, value: str, info: ValidationInfo) -> str:
        violation = password_policy_violation(value, info.data.get("email"))
        if violation:
            raise ValueError(violation)
        return value


class LoginRequest(RequestModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)

    _lower_email = field_validator("email")(_normalize_email)


class RefreshRequest(RequestModel):
    refresh_token: str = _OPAQUE_TOKEN


class TokenPair(ResponseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105 - OAuth2 token type, not a secret
    expires_in: int = Field(description="Access token lifetime in seconds.")
    refresh_expires_in: int = Field(description="Refresh token lifetime in seconds.")


class AuthResponse(ResponseModel):
    user: UserResponse
    tokens: TokenPair
