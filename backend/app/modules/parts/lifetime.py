"""Expected lifetime of installed parts (no I/O)."""

from datetime import date

from app.modules.maintenance.calculator import DueBaseline, DueRule, DueState, compute_due
from app.modules.parts.models import PartReplacement

PART_WARNING_KM = 1000
PART_WARNING_DAYS = 30


def evaluate_part(part: PartReplacement, current_mileage: int, today: date) -> DueState | None:
    """Wear status of an installed part with an expected lifetime (None otherwise)."""
    if not part.is_installed or (
        part.expected_lifetime_km is None and part.expected_lifetime_months is None
    ):
        return None
    rule = DueRule(
        interval_km=part.expected_lifetime_km,
        interval_months=part.expected_lifetime_months,
        warning_km=PART_WARNING_KM,
        warning_days=PART_WARNING_DAYS,
    )
    baseline = DueBaseline(last_date=part.installed_date, last_mileage=part.installed_mileage)
    return compute_due(rule, baseline, current_mileage, today)
