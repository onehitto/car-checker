"""Current status of a maintenance schedule (no I/O)."""

from datetime import date

from app.modules.maintenance.calculator import DueState, DueStatus, evaluate_due
from app.modules.maintenance.models import MaintenanceSchedule


def evaluate_schedule(schedule: MaintenanceSchedule, current_mileage: int, today: date) -> DueState:
    """Status of a schedule now. Disabled schedules are always OK."""
    state = evaluate_due(
        schedule.next_service_date,
        schedule.next_service_mileage,
        current_mileage,
        today,
        schedule.warning_before_km,
        schedule.warning_before_days,
    )
    if not schedule.enabled:
        return DueState(
            state.next_service_date,
            state.next_service_mileage,
            state.remaining_km,
            state.remaining_days,
            state.overdue_km,
            state.overdue_days,
            DueStatus.OK,
            None,
        )
    return state
