from app.core.logging import REDACTED, redact_sensitive_values


def test_sensitive_top_level_keys_are_redacted() -> None:
    event = redact_sensitive_values(
        None,
        "info",
        {
            "event": "auth.login_failed",
            "password": "hunter2",
            "refresh_token": "abc",
            "Authorization": "Bearer xyz",
            "user_id": "42",
        },
    )
    assert event == {
        "event": "auth.login_failed",
        "password": REDACTED,
        "refresh_token": REDACTED,
        "Authorization": REDACTED,
        "user_id": "42",
    }


def test_nested_structures_are_redacted() -> None:
    event = redact_sensitive_values(
        None,
        "info",
        {
            "event": "x",
            "payload": {"user": {"email": "a@b.c", "name": "A"}, "items": [{"jwt_token": "t"}]},
        },
    )
    assert event["payload"] == {
        "user": {"email": REDACTED, "name": "A"},
        "items": [{"jwt_token": REDACTED}],
    }


def test_event_message_is_never_redacted() -> None:
    assert redact_sensitive_values(None, "info", {"event": "token refreshed"})["event"] == (
        "token refreshed"
    )
