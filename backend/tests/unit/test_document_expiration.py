from datetime import date, timedelta

import pytest

from app.modules.documents.expiration import (
    DEFAULT_REMINDER_DAYS,
    DocumentStatus,
    document_state,
    normalize_reminder_days,
)

TODAY = date(2026, 10, 6)


def in_days(days: int) -> date:
    return TODAY + timedelta(days=days)


@pytest.mark.parametrize(
    ("days_left", "status", "reminder"),
    [
        (120, DocumentStatus.VALID, None),
        (31, DocumentStatus.VALID, None),
        (30, DocumentStatus.EXPIRING_SOON, 30),
        (12, DocumentStatus.EXPIRING_SOON, 30),
        (7, DocumentStatus.EXPIRING_SOON, 7),
        (2, DocumentStatus.EXPIRING_SOON, 7),
        (1, DocumentStatus.EXPIRING_SOON, 1),
        (0, DocumentStatus.EXPIRING_SOON, 0),
        (-1, DocumentStatus.EXPIRED, None),
    ],
)
def test_default_reminders(days_left: int, status: DocumentStatus, reminder: int | None) -> None:
    state = document_state(in_days(days_left), DEFAULT_REMINDER_DAYS, TODAY)
    assert (state.status, state.days_until_expiration, state.active_reminder) == (
        status,
        days_left,
        reminder,
    )


def test_expiring_soon_window_follows_largest_reminder() -> None:
    reminders = [90, 30, 15, 7, 1, 0]
    state = document_state(in_days(80), reminders, TODAY)
    assert (state.status, state.active_reminder) == (DocumentStatus.EXPIRING_SOON, 90)
    assert document_state(in_days(91), reminders, TODAY).status is DocumentStatus.VALID


def test_no_reminders_uses_thirty_day_window() -> None:
    state = document_state(in_days(20), [], TODAY)
    assert (state.status, state.active_reminder) == (DocumentStatus.EXPIRING_SOON, None)


def test_document_without_expiration_is_valid() -> None:
    state = document_state(None, DEFAULT_REMINDER_DAYS, TODAY)
    assert (state.status, state.days_until_expiration) == (DocumentStatus.VALID, None)


def test_normalize_reminder_days() -> None:
    assert normalize_reminder_days([7, 30, 7, 0]) == [30, 7, 0]
    with pytest.raises(ValueError, match="between 0 and 365"):
        normalize_reminder_days([400])
    with pytest.raises(ValueError, match="at most 10"):
        normalize_reminder_days(list(range(11)))
