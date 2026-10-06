import json
from pathlib import Path

import pytest

from app.core.i18n import Language, has_translation, load_catalog, resolve_language, translate

LOCALES = Path(__file__).resolve().parents[2] / "app" / "core" / "i18n" / "locales"


def test_translates_with_parameters() -> None:
    subject = translate("email.password_reset.subject", "fr")
    assert subject == "Réinitialisez votre mot de passe Car Checker"
    body = translate(
        "email.password_reset.body",
        "en",
        first_name="Amina",
        reset_url="https://x",
        expires_minutes=30,
    )
    assert "Hello Amina" in body
    assert "https://x" in body


def test_unknown_language_falls_back_to_english() -> None:
    assert resolve_language("de") is Language.EN
    assert translate("email.password_reset.subject", "de") == "Reset your Car Checker password"


def test_unknown_key_returns_key_and_missing_params_are_kept() -> None:
    assert translate("does.not.exist", "ar") == "does.not.exist"
    assert "{reset_url}" in translate("email.password_reset.body", "en", first_name="A")
    assert has_translation("email.password_reset.body")
    assert not has_translation("does.not.exist")


@pytest.mark.parametrize("language", [Language.FR, Language.AR])
def test_every_catalog_has_the_same_keys_as_english(language: Language) -> None:
    assert set(load_catalog(language)) == set(load_catalog(Language.EN))


@pytest.mark.parametrize("path", sorted(LOCALES.glob("*.json")))
def test_catalog_files_are_valid_json(path: Path) -> None:
    assert isinstance(json.loads(path.read_text(encoding="utf-8")), dict)


def test_context_language_is_used_by_default() -> None:
    from app.core.i18n import get_current_language, use_language

    with use_language("fr"):
        assert get_current_language() is Language.FR
        assert translate("email.password_reset.subject") == (
            "Réinitialisez votre mot de passe Car Checker"
        )
        assert translate("email.password_reset.subject", "en").startswith("Reset")
    assert get_current_language() is Language.EN
