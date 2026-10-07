"""Status of a custom reminder (no I/O)."""

from datetime import date

from app.modules.alerts.models import Reminder
from app.modules.maintenance.calculator import DueState, evaluate_due


def evaluate_reminder(reminder: Reminder, current_mileage: int, today: date) -> DueState:
    return evaluate_due(
        reminder.due_date,
        reminder.due_mileage,
        current_mileage,
        today,
        reminder.warning_before_km,
        reminder.warning_before_days,
    )
