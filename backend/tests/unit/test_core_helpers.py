from datetime import UTC, date, datetime

import pytest

from app.core.clock import FixedClock
from app.core.dates import add_months, month_key, months_between
from app.core.ids import uuid7
from app.core.units import ConsumptionUnit, DistanceUnit, convert_consumption, convert_distance


class TestUuid7:
    def test_version_and_variant(self) -> None:
        value = uuid7()
        assert value.version == 7
        assert value.variant == "specified in RFC 4122"

    def test_values_are_time_ordered_and_unique(self) -> None:
        values = [uuid7() for _ in range(1000)]
        assert len(set(values)) == 1000
        timestamps = [v.int >> 80 for v in values]
        assert timestamps == sorted(timestamps)


class TestAddMonths:
    @pytest.mark.parametrize(
        ("start", "months", "expected"),
        [
            (date(2025, 11, 1), 12, date(2026, 11, 1)),
            (date(2026, 1, 31), 1, date(2026, 2, 28)),
            (date(2028, 1, 31), 1, date(2028, 2, 29)),
            (date(2026, 12, 15), 1, date(2027, 1, 15)),
            (date(2026, 3, 31), -1, date(2026, 2, 28)),
            (date(2026, 5, 10), 0, date(2026, 5, 10)),
        ],
    )
    def test_add_months(self, start: date, months: int, expected: date) -> None:
        assert add_months(start, months) == expected

    def test_months_between_is_inclusive_and_symmetric(self) -> None:
        assert months_between(date(2026, 1, 15), date(2026, 1, 20)) == 1
        assert months_between(date(2025, 11, 1), date(2026, 2, 1)) == 4
        assert months_between(date(2026, 2, 1), date(2025, 11, 1)) == 4

    def test_month_key(self) -> None:
        assert month_key(date(2026, 3, 9)) == "2026-03"


class TestClock:
    def test_today_depends_on_time_zone(self) -> None:
        clock = FixedClock(datetime(2026, 10, 6, 23, 30, tzinfo=UTC))
        assert clock.today("UTC") == date(2026, 10, 6)
        assert clock.today("Africa/Casablanca") == date(2026, 10, 7)
        assert clock.today("America/New_York") == date(2026, 10, 6)

    def test_unknown_time_zone_falls_back_to_utc(self) -> None:
        clock = FixedClock(datetime(2026, 10, 6, 23, 30, tzinfo=UTC))
        assert clock.today("Not/AZone") == date(2026, 10, 6)

    def test_naive_datetimes_are_rejected(self) -> None:
        with pytest.raises(ValueError, match="timezone-aware"):
            FixedClock(datetime(2026, 1, 1))


class TestUnits:
    def test_distance(self) -> None:
        assert convert_distance(100, DistanceUnit.KM) == 100
        assert convert_distance(160.9344, DistanceUnit.MI) == pytest.approx(100)

    @pytest.mark.parametrize(
        ("unit", "expected"),
        [
            (ConsumptionUnit.L_100KM, 5.0),
            (ConsumptionUnit.KM_L, 20.0),
            (ConsumptionUnit.MPG_US, 47.04),
            (ConsumptionUnit.MPG_UK, 56.50),
        ],
    )
    def test_consumption(self, unit: ConsumptionUnit, expected: float) -> None:
        assert convert_consumption(5.0, unit) == pytest.approx(expected, abs=0.01)

    def test_inverse_units_reject_zero(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            convert_consumption(0, ConsumptionUnit.KM_L)
