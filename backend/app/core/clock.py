"""Injectable clock so that date-dependent logic is deterministic in tests."""

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def zone(tz_name: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(tz_name or "UTC")
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("UTC")


class Clock:
    """System clock. Always returns timezone-aware UTC datetimes."""

    def now(self) -> datetime:
        return datetime.now(UTC)

    def today(self, tz_name: str | None = "UTC") -> date:
        """Calendar date "today" for a user living in `tz_name`."""
        return self.now().astimezone(zone(tz_name)).date()


class FixedClock(Clock):
    """Clock frozen at a given instant (tests, simulations)."""

    def __init__(self, instant: datetime) -> None:
        if instant.tzinfo is None:
            raise ValueError("FixedClock requires a timezone-aware datetime")
        self._instant = instant

    def now(self) -> datetime:
        return self._instant

    def set(self, instant: datetime) -> None:
        self._instant = instant


_system_clock = Clock()


def get_clock() -> Clock:
    """FastAPI dependency; override with `app.dependency_overrides[get_clock]` in tests."""
    return _system_clock
