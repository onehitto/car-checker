"""Document expiration status (pure functions). See docs/05-domain-logic.md, section 15."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

DEFAULT_REMINDER_DAYS = (30, 7, 1, 0)
DEFAULT_EXPIRING_SOON_DAYS = 30
MAX_REMINDER_DAYS = 365
MAX_REMINDERS = 10


class DocumentStatus(StrEnum):
    VALID = "valid"
    EXPIRING_SOON = "expiring_soon"
    EXPIRED = "expired"


@dataclass(frozen=True, slots=True)
class ExpirationState:
    status: DocumentStatus
    days_until_expiration: int | None
    active_reminder: int | None  # reminder offset (days before) reached, if any


def normalize_reminder_days(values: Sequence[int]) -> list[int]:
    """Unique offsets sorted from the farthest to the closest (largest first)."""
    if len(set(values)) > MAX_REMINDERS:
        raise ValueError(f"Configure at most {MAX_REMINDERS} reminders.")
    if any(not 0 <= value <= MAX_REMINDER_DAYS for value in values):
        raise ValueError(f"Reminder offsets must be between 0 and {MAX_REMINDER_DAYS} days.")
    return sorted(set(values), reverse=True)


def expiring_soon_window(reminder_days: Sequence[int]) -> int:
    return max(reminder_days) if reminder_days else DEFAULT_EXPIRING_SOON_DAYS


def document_state(
    expiration_date: date | None, reminder_days: Sequence[int], today: date
) -> ExpirationState:
    if expiration_date is None:
        return ExpirationState(DocumentStatus.VALID, None, None)
    days_left = (expiration_date - today).days
    if days_left < 0:
        return ExpirationState(DocumentStatus.EXPIRED, days_left, None)
    status = (
        DocumentStatus.EXPIRING_SOON
        if days_left <= expiring_soon_window(reminder_days)
        else DocumentStatus.VALID
    )
    reached = [offset for offset in reminder_days if offset >= days_left]
    return ExpirationState(status, days_left, min(reached) if reached else None)
