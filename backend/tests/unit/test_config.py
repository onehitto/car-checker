import pytest
from pydantic import ValidationError

from app.core.config import DEV_JWT_SECRET, Environment, Settings

STRONG_SECRET = "x" * 48
OTHER_STRONG_SECRET = "y" * 48


def make_settings(**overrides: object) -> Settings:
    return Settings(_env_file=None, **overrides)  # type: ignore[call-arg]


def test_cors_origins_are_parsed_from_comma_separated_string() -> None:
    settings = make_settings(cors_origins="https://a.example, https://b.example ,")
    assert settings.cors_origins == ["https://a.example", "https://b.example"]


def test_docs_enabled_by_default_outside_production() -> None:
    assert make_settings(app_env=Environment.DEVELOPMENT).docs_enabled is True


def test_production_requires_real_secrets() -> None:
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        make_settings(app_env=Environment.PRODUCTION, jwt_secret=DEV_JWT_SECRET)


def test_production_rejects_short_secrets() -> None:
    with pytest.raises(ValidationError, match="at least"):
        make_settings(
            app_env=Environment.PRODUCTION, jwt_secret="short", jwt_refresh_secret=STRONG_SECRET
        )


def test_production_rejects_identical_secrets() -> None:
    with pytest.raises(ValidationError, match="must be different"):
        make_settings(
            app_env=Environment.PRODUCTION,
            jwt_secret=STRONG_SECRET,
            jwt_refresh_secret=STRONG_SECRET,
        )


def test_production_accepts_strong_secrets_and_disables_docs() -> None:
    settings = make_settings(
        app_env=Environment.PRODUCTION,
        jwt_secret=STRONG_SECRET,
        jwt_refresh_secret=OTHER_STRONG_SECRET,
    )
    assert settings.is_production
    assert settings.docs_enabled is False
