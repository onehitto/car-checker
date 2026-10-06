"""Calendar arithmetic helpers."""

import calendar
from datetime import date


def add_months(start: date, months: int) -> date:
    """Add calendar months, clamping the day (Jan 31 + 1 month = Feb 28/29)."""
    month_index = start.month - 1 + months
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    day = min(start.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def months_between(start: date, end: date) -> int:
    """Number of calendar months touched by the inclusive range [start, end] (at least 1)."""
    if end < start:
        start, end = end, start
    return (end.year - start.year) * 12 + (end.month - start.month) + 1


def month_key(value: date) -> str:
    return f"{value.year:04d}-{value.month:02d}"
