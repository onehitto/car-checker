from datetime import date

import pytest

from app.modules.maintenance.calculator import (
    DueBaseline,
    DueRule,
    DueStatus,
    compute_due,
    dimension_status,
    evaluate_due,
    next_service,
)

TODAY = date(2026, 10, 6)
OIL = DueRule(interval_km=10_000, interval_months=12, warning_km=1_000, warning_days=30)


class TestDimensionStatus:
    @pytest.mark.parametrize(
        ("remaining", "expected"),
        [
            (-1, DueStatus.OVERDUE),
            (0, DueStatus.DUE),
            (300, DueStatus.DUE),
            (301, DueStatus.DUE_SOON),
            (1_000, DueStatus.DUE_SOON),
            (1_001, DueStatus.UPCOMING),
            (2_000, DueStatus.UPCOMING),
            (2_001, DueStatus.OK),
        ],
    )
    def test_km_windows(self, remaining: int, expected: DueStatus) -> None:
        assert dimension_status(remaining, warning=1_000, due_window=300) is expected

    @pytest.mark.parametrize(
        ("remaining", "expected"),
        [
            (-3, DueStatus.OVERDUE),
            (7, DueStatus.DUE),
            (8, DueStatus.DUE_SOON),
            (45, DueStatus.UPCOMING),
            (61, DueStatus.OK),
        ],
    )
    def test_day_windows(self, remaining: int, expected: DueStatus) -> None:
        assert dimension_status(remaining, warning=30, due_window=7) is expected

    def test_due_window_never_exceeds_warning(self) -> None:
        assert dimension_status(100, warning=50, due_window=300) is DueStatus.UPCOMING
        assert dimension_status(50, warning=50, due_window=300) is DueStatus.DUE

    def test_zero_warning(self) -> None:
        assert dimension_status(0, warning=0, due_window=300) is DueStatus.DUE
        assert dimension_status(1, warning=0, due_window=300) is DueStatus.OK

    def test_unknown_dimension(self) -> None:
        assert dimension_status(None, warning=30, due_window=7) is None


class TestNextService:
    def test_from_last_service(self) -> None:
        baseline = DueBaseline(last_date=date(2025, 11, 1), last_mileage=50_000)
        assert next_service(OIL, baseline) == (date(2026, 11, 1), 60_000)

    def test_explicit_next_used_without_history(self) -> None:
        baseline = DueBaseline(explicit_next_date=date(2027, 1, 1), explicit_next_mileage=15_000)
        assert next_service(OIL, baseline) == (date(2027, 1, 1), 15_000)

    def test_last_service_wins_over_explicit_next(self) -> None:
        baseline = DueBaseline(
            last_date=date(2025, 11, 1),
            last_mileage=50_000,
            explicit_next_date=date(2030, 1, 1),
            explicit_next_mileage=99_999,
        )
        assert next_service(OIL, baseline) == (date(2026, 11, 1), 60_000)

    def test_vehicle_baseline_as_last_resort(self) -> None:
        baseline = DueBaseline(fallback_date=date(2026, 3, 31), fallback_mileage=80_000)
        assert next_service(OIL, baseline) == (date(2027, 3, 31), 90_000)

    def test_month_end_is_clamped(self) -> None:
        rule = DueRule(interval_km=None, interval_months=1, warning_km=0, warning_days=0)
        assert next_service(rule, DueBaseline(last_date=date(2026, 1, 31))) == (
            date(2026, 2, 28),
            None,
        )

    def test_mileage_only_rule_ignores_dates(self) -> None:
        rule = DueRule(interval_km=40_000, interval_months=None, warning_km=1_000, warning_days=30)
        baseline = DueBaseline(last_date=date(2025, 1, 1), last_mileage=60_000)
        assert next_service(rule, baseline) == (None, 100_000)

    def test_nothing_known(self) -> None:
        assert next_service(OIL, DueBaseline()) == (None, None)


class TestEvaluate:
    def test_documented_example(self) -> None:
        """docs/05-domain-logic.md: oil change due soon on both dimensions."""
        state = compute_due(
            OIL,
            DueBaseline(last_date=date(2025, 11, 1), last_mileage=50_000),
            current_mileage=59_400,
            today=TODAY,
        )
        assert state.next_service_date == date(2026, 11, 1)
        assert state.next_service_mileage == 60_000
        assert (state.remaining_km, state.remaining_days) == (600, 26)
        assert (state.overdue_km, state.overdue_days) == (0, 0)
        assert state.status is DueStatus.DUE_SOON
        assert state.due_reason == "both"

    def test_whichever_comes_first(self) -> None:
        state = evaluate_due(
            next_date=date(2027, 6, 1),
            next_mileage=60_000,
            current_mileage=60_450,
            today=TODAY,
            warning_km=1_000,
            warning_days=30,
        )
        assert state.status is DueStatus.OVERDUE
        assert state.overdue_km == 450
        assert state.due_reason == "mileage"

    def test_overdue_by_date(self) -> None:
        state = evaluate_due(
            next_date=date(2026, 9, 1),
            next_mileage=None,
            current_mileage=1,
            today=TODAY,
            warning_km=1_000,
            warning_days=30,
        )
        assert (state.status, state.overdue_days, state.remaining_days) == (
            DueStatus.OVERDUE,
            35,
            -35,
        )
        assert state.remaining_km is None
        assert state.overdue_km is None
        assert state.due_reason == "date"

    def test_ok_has_no_reason(self) -> None:
        state = evaluate_due(
            next_date=date(2027, 10, 1),
            next_mileage=100_000,
            current_mileage=50_000,
            today=TODAY,
            warning_km=1_000,
            warning_days=30,
        )
        assert state.status is DueStatus.OK
        assert state.due_reason is None

    def test_unknown_when_nothing_computable(self) -> None:
        state = evaluate_due(None, None, 50_000, TODAY, 1_000, 30)
        assert state.status is DueStatus.UNKNOWN

    def test_severity_order(self) -> None:
        ordered = [
            DueStatus.UNKNOWN,
            DueStatus.OK,
            DueStatus.UPCOMING,
            DueStatus.DUE_SOON,
            DueStatus.DUE,
            DueStatus.OVERDUE,
        ]
        assert [s.severity for s in ordered] == sorted(s.severity for s in ordered)
        assert DueStatus.DUE.is_at_least(DueStatus.DUE_SOON)
        assert not DueStatus.UPCOMING.is_at_least(DueStatus.DUE_SOON)
