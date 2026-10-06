"""Application settings loaded from environment variables (and an optional `.env` file)."""

from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# Development-only placeholders. Startup is refused in production while they are in use.
DEV_JWT_SECRET = "dev-only-jwt-secret-change-me-0123456789abcdef"  # noqa: S105
DEV_JWT_REFRESH_SECRET = "dev-only-refresh-secret-change-me-0123456789ab"  # noqa: S105
MIN_SECRET_LENGTH = 32


class Environment(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Application -------------------------------------------------------------------------
    app_name: str = "Car Checker API"
    app_version: str = "0.1.0"
    app_env: Environment = Environment.DEVELOPMENT
    api_port: int = 8000
    api_v1_prefix: str = "/api/v1"
    enable_docs: bool | None = Field(
        default=None, description="Expose Swagger UI/OpenAPI. Defaults to true outside production."
    )

    # --- Database ----------------------------------------------------------------------------
    database_url: str = "postgresql+asyncpg://car_checker:car_checker@localhost:5432/car_checker"
    test_database_url: str = (
        "postgresql+asyncpg://car_checker:car_checker@localhost:5432/car_checker_test"
    )
    database_pool_size: int = Field(default=10, ge=1)
    database_max_overflow: int = Field(default=10, ge=0)
    database_echo: bool = False

    # --- Authentication ----------------------------------------------------------------------
    jwt_secret: SecretStr = SecretStr(DEV_JWT_SECRET)
    jwt_refresh_secret: SecretStr = SecretStr(DEV_JWT_REFRESH_SECRET)
    jwt_algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"
    jwt_issuer: str = "car-checker"
    jwt_audience: str = "car-checker-clients"
    access_token_expires_in: int = Field(default=900, ge=60, description="Seconds")
    refresh_token_expires_in: int = Field(default=30 * 24 * 3600, ge=3600, description="Seconds")
    password_reset_expires_in: int = Field(default=1800, ge=300, description="Seconds")

    # --- HTTP ----------------------------------------------------------------------------------
    cors_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]
    rate_limit_enabled: bool = True
    rate_limit_default: str = "300/minute"
    rate_limit_auth: str = "10/minute"
    rate_limit_upload: str = "30/minute"
    redis_url: str | None = None

    # --- Files ---------------------------------------------------------------------------------
    storage_backend: Literal["local"] = "local"
    upload_directory: Path = Path("var/uploads")
    max_upload_size: int = Field(default=10 * 1024 * 1024, ge=1024, description="Bytes")

    # --- Logging -------------------------------------------------------------------------------
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_format: Literal["console", "json"] = "console"

    # --- Email / notifications -------------------------------------------------------------------
    email_backend: Literal["console", "smtp", "memory"] = "console"
    email_from: str = "Car Checker <no-reply@carchecker.local>"
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None
    smtp_starttls: bool = True
    frontend_url: str = "http://localhost:3000"
    password_reset_path: str = "/reset-password"  # noqa: S105 - URL path, not a secret

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("redis_url", "smtp_host", "smtp_username", mode="before")
    @classmethod
    def _empty_string_is_none(cls, value: object) -> object:
        return None if value == "" else value

    @model_validator(mode="after")
    def _check_production_safety(self) -> "Settings":
        if self.app_env is not Environment.PRODUCTION:
            return self
        for name, secret, placeholder in (
            ("JWT_SECRET", self.jwt_secret, DEV_JWT_SECRET),
            ("JWT_REFRESH_SECRET", self.jwt_refresh_secret, DEV_JWT_REFRESH_SECRET),
        ):
            value = secret.get_secret_value()
            if value == placeholder or len(value) < MIN_SECRET_LENGTH:
                raise ValueError(
                    f"{name} must be set to a random value of at least "
                    f"{MIN_SECRET_LENGTH} characters in production."
                )
        if self.jwt_secret.get_secret_value() == self.jwt_refresh_secret.get_secret_value():
            raise ValueError("JWT_SECRET and JWT_REFRESH_SECRET must be different.")
        if "*" in self.cors_origins:
            raise ValueError("CORS_ORIGINS must not contain '*' in production.")
        if self.email_backend == "memory":
            raise ValueError("EMAIL_BACKEND=memory is only allowed in tests.")
        return self

    @property
    def is_production(self) -> bool:
        return self.app_env is Environment.PRODUCTION

    @property
    def docs_enabled(self) -> bool:
        return self.enable_docs if self.enable_docs is not None else not self.is_production


@lru_cache
def get_settings() -> Settings:
    return Settings()
