import uuid
from datetime import date
from decimal import Decimal

import pytest

from app.modules.fuel.calculator import FillUp, analyze, resolve_prices, summarize


def fill(
    mileage: int,
    liters: str,
    price: str | None = None,
    *,
    full: bool = True,
    missed: bool = False,
    day: int = 1,
    month: int = 1,
) -> FillUp:
    return FillUp(
        id=uuid.uuid4(),
        fill_date=date(2026, month, day),
        mileage=mileage,
        liters=Decimal(liters),
        total_price=Decimal(price) if price else None,
        full_tank=full,
        missed_previous=missed,
    )


class TestAnalyze:
    def test_consecutive_full_tanks(self) -> None:
        first, second = fill(10_000, "40"), fill(10_600, "42", "84", day=10)
        metrics, segments = analyze([second, first])  # order does not matter
        assert metrics[first.id].consumption_l_100km is None
        assert metrics[first.id].distance_since_previous is None
        assert metrics[second.id].distance_since_previous == 600
        assert metrics[second.id].consumption_l_100km == pytest.approx(7.0)
        assert len(segments) == 1
        assert segments[0].cost == Decimal("84")

    def test_partial_fill_ups_are_accumulated(self) -> None:
        fills = [
            fill(10_000, "40"),
            fill(10_300, "15", full=False, day=5),
            fill(10_800, "33", day=9),
        ]
        metrics, segments = analyze(fills)
        assert metrics[fills[1].id].consumption_l_100km is None
        assert metrics[fills[1].id].distance_since_previous == 300
        assert metrics[fills[2].id].consumption_l_100km == pytest.approx(48 / 800 * 100)
        assert segments[0].distance == 800

    def test_missed_fill_up_breaks_the_chain(self) -> None:
        fills = [
            fill(10_000, "40"),
            fill(10_900, "30", missed=True, day=8),
            fill(11_500, "36", day=15),
        ]
        metrics, _ = analyze(fills)
        assert metrics[fills[1].id].consumption_l_100km is None
        assert metrics[fills[2].id].consumption_l_100km == pytest.approx(6.0)

    def test_start_with_partial_fill_up(self) -> None:
        fills = [
            fill(9_800, "10", full=False),
            fill(10_000, "40", day=2),
            fill(10_500, "30", day=9),
        ]
        metrics, _ = analyze(fills)
        assert metrics[fills[1].id].consumption_l_100km is None
        assert metrics[fills[2].id].consumption_l_100km == pytest.approx(6.0)

    def test_unknown_price_makes_segment_cost_unknown(self) -> None:
        fills = [fill(10_000, "40"), fill(10_300, "15", full=False), fill(10_800, "33", "70")]
        _, segments = analyze(fills)
        assert segments[0].cost is None


class TestSummarize:
    def test_distance_weighted_average_and_costs(self) -> None:
        fills = [
            fill(10_000, "40", "80", day=1),
            fill(10_500, "30", "60", day=10),  # 6.0 L/100 km over 500 km
            fill(11_500, "80", "160", month=2, day=1),  # 8.0 L/100 km over 1000 km
        ]
        stats = summarize(fills)
        assert stats.fill_up_count == 3
        assert stats.total_liters == Decimal("150")
        assert stats.total_cost == Decimal("300")
        assert stats.average_consumption_l_100km == pytest.approx(110 / 1500 * 100)
        assert stats.last_consumption_l_100km == pytest.approx(8.0)
        assert stats.cost_per_km == pytest.approx(220 / 1500)
        assert stats.average_price_per_liter == pytest.approx(2.0)
        assert stats.distance_tracked == 1500
        assert [(m.month, m.liters, m.cost) for m in stats.monthly] == [
            ("2026-01", Decimal("70"), Decimal("140")),
            ("2026-02", Decimal("80"), Decimal("160")),
        ]

    def test_empty(self) -> None:
        stats = summarize([])
        assert stats.fill_up_count == 0
        assert stats.average_consumption_l_100km is None
        assert stats.cost_per_km is None


class TestResolvePrices:
    def test_total_from_unit_price(self) -> None:
        assert resolve_prices(Decimal("42.3"), Decimal("1.89"), None) == (
            Decimal("1.89"),
            Decimal("79.95"),
        )

    def test_unit_price_from_total(self) -> None:
        assert resolve_prices(Decimal("40"), None, Decimal("80")) == (
            Decimal("2.0000"),
            Decimal("80"),
        )

    def test_consistency_is_checked(self) -> None:
        assert resolve_prices(Decimal("40"), Decimal("2"), Decimal("80.04")) == (
            Decimal("2"),
            Decimal("80.04"),
        )
        with pytest.raises(ValueError, match="does not match"):
            resolve_prices(Decimal("40"), Decimal("2"), Decimal("90"))

    def test_nothing_known(self) -> None:
        assert resolve_prices(Decimal("40"), None, None) == (None, None)
