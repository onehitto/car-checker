"""Maintenance due-date calculation (pure functions, no I/O).

See docs/05-domain-logic.md, section 13. `today` and `current_mileage` are always passed in,
so results are deterministic and the same functions serve schedules, part lifetimes and
custom reminders.
"""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Literal

from app.core.dates import add_months

DUE_WINDOW_KM = 300
DUE_WINDOW_DAYS = 7

DueReason = Literal["mileage", "date", "both"]


class DueStatus(StrEnum):
    UNKNOWN = "unknown"
    OK = "ok"
    UPCOMING = "upcoming"
    DUE_SOON = "due_soon"
    DUE = "due"
    OVERDUE = "overdue"

    @property
    def severity(self) -> int:
        return _SEVERITY[self]

    def is_at_least(self, other: "DueStatus") -> bool:
        return self.severity >= other.severity


_SEVERITY = {status: rank for rank, status in enumerate(DueStatus)}


@dataclass(frozen=True, slots=True)
class DueRule:
    """Recurrence: every `interval_km` and/or `interval_months`, with warning windows."""

    interval_km: int | None
    interval_months: int | None
    warning_km: int
    warning_days: int


@dataclass(frozen=True, slots=True)
class DueBaseline:
    """What is known about the previous occurrence, by decreasing priority."""

    last_date: date | None = None
    last_mileage: int | None = None
    explicit_next_date: date | None = None
    explicit_next_mileage: int | None = None
    fallback_date: date | None = None  # e.g. vehicle purchase date
    fallback_mileage: int | None = None  # e.g. vehicle initial mileage


@dataclass(frozen=True, slots=True)
class DueState:
    next_service_date: date | None
    next_service_mileage: int | None
    remaining_km: int | None
    remaining_days: int | None
    overdue_km: int | None
    overdue_days: int | None
    status: DueStatus
    due_reason: DueReason | None


def next_service(rule: DueRule, baseline: DueBaseline) -> tuple[date | None, int | None]:
    """Next due date and mileage: last service + interval, else explicit, else baseline."""
    next_mileage: int | None = None
    if rule.interval_km:
        if baseline.last_mileage is not None:
            next_mileage = baseline.last_mileage + rule.interval_km
        elif baseline.explicit_next_mileage is not None:
            next_mileage = baseline.explicit_next_mileage
        elif baseline.fallback_mileage is not None:
            next_mileage = baseline.fallback_mileage + rule.interval_km
    else:
        next_mileage = baseline.explicit_next_mileage

    next_date: date | None = None
    if rule.interval_months:
        if baseline.last_date is not None:
            next_date = add_months(baseline.last_date, rule.interval_months)
        elif baseline.explicit_next_date is not None:
            next_date = baseline.explicit_next_date
        elif baseline.fallback_date is not None:
            next_date = add_months(baseline.fallback_date, rule.interval_months)
    else:
        next_date = baseline.explicit_next_date

    return next_date, next_mileage


def dimension_status(remaining: int | None, warning: int, due_window: int) -> DueStatus | None:
    """Status of one dimension (km or days); None when it cannot be computed."""
    if remaining is None:
        return None
    if remaining < 0:
        return DueStatus.OVERDUE
    if remaining <= min(due_window, warning):
        return DueStatus.DUE
    if remaining <= warning:
        return DueStatus.DUE_SOON
    if remaining <= 2 * warning:
        return DueStatus.UPCOMING
    return DueStatus.OK


def evaluate_due(
    next_date: date | None,
    next_mileage: int | None,
    current_mileage: int,
    today: date,
    warning_km: int,
    warning_days: int,
) -> DueState:
    """Status = the most severe dimension ("whichever comes first")."""
    remaining_km = next_mileage - current_mileage if next_mileage is not None else None
    remaining_days = (next_date - today).days if next_date is not None else None
    km_status = dimension_status(remaining_km, warning_km, DUE_WINDOW_KM)
    day_status = dimension_status(remaining_days, warning_days, DUE_WINDOW_DAYS)

    known = [s for s in (km_status, day_status) if s is not None]
    status = max(known, key=lambda s: s.severity) if known else DueStatus.UNKNOWN

    reason: DueReason | None = None
    if status.is_at_least(DueStatus.UPCOMING):
        by_km, by_date = km_status is status, day_status is status
        reason = "both" if by_km and by_date else "mileage" if by_km else "date"

    return DueState(
        next_service_date=next_date,
        next_service_mileage=next_mileage,
        remaining_km=remaining_km,
        remaining_days=remaining_days,
        overdue_km=max(0, -remaining_km) if remaining_km is not None else None,
        overdue_days=max(0, -remaining_days) if remaining_days is not None else None,
        status=status,
        due_reason=reason,
    )


def compute_due(
    rule: DueRule, baseline: DueBaseline, current_mileage: int, today: date
) -> DueState:
    next_date, next_mileage = next_service(rule, baseline)
    return evaluate_due(
        next_date, next_mileage, current_mileage, today, rule.warning_km, rule.warning_days
    )
