"""Alert rules: which alert (if any) a source deserves right now. Pure functions.

Each rule returns a `DesiredAlert` whose `dedup_key` encodes the source, the deadline and the
severity, so the engine can create it once, escalate it, and resolve it when it no longer
applies. Text is rendered per recipient language from the i18n catalog.
"""

import uuid
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from app.core.i18n import Language, has_translation, translate
from app.modules.alerts.models import AlertPriority, AlertSource, AlertType
from app.modules.documents.expiration import DocumentStatus, document_state
from app.modules.documents.models import DocumentType, VehicleDocument
from app.modules.maintenance.calculator import DueState, DueStatus
from app.modules.maintenance.models import MaintenanceSchedule
from app.modules.parts.models import PartReplacement
from app.modules.vehicles.models import Vehicle

MILEAGE_STALE_DAYS = 30

DUE_PRIORITY = {
    DueStatus.UPCOMING: AlertPriority.LOW,
    DueStatus.DUE_SOON: AlertPriority.MEDIUM,
    DueStatus.DUE: AlertPriority.HIGH,
    DueStatus.OVERDUE: AlertPriority.CRITICAL,
}
DOCUMENT_ALERT_TYPES = {
    DocumentType.INSURANCE: AlertType.INSURANCE_EXPIRATION,
    DocumentType.TECHNICAL_INSPECTION: AlertType.INSPECTION_DUE,
}


@dataclass(frozen=True, slots=True)
class Text:
    """Translatable fragment: catalog `key` rendered with `params`, else `fallback`."""

    key: str | None
    fallback: str = ""
    params: dict[str, Any] = field(default_factory=dict)

    def resolve(self, language: Language) -> str:
        if self.key and has_translation(self.key, language):
            return translate(self.key, language, **self.params)
        return self.fallback


@dataclass(frozen=True, slots=True)
class RenderedAlert:
    title: str
    message: str
    params: dict[str, Any]


@dataclass(frozen=True, slots=True)
class DesiredAlert:
    source_type: AlertSource
    source_id: uuid.UUID
    alert_type: AlertType
    priority: AlertPriority
    dedup_key: str
    template: str
    params: dict[str, Any]
    trigger_date: date | None = None
    trigger_mileage: int | None = None

    @property
    def source(self) -> tuple[AlertSource, uuid.UUID]:
        return self.source_type, self.source_id

    def render(self, language: Language) -> RenderedAlert:
        resolved = {
            name: value.resolve(language)
            if isinstance(value, Text)
            else value.isoformat()
            if isinstance(value, date)
            else value
            for name, value in self.params.items()
        }
        return RenderedAlert(
            title=translate(f"{self.template}.title", language, **resolved)[:200],
            message=translate(f"{self.template}.message", language, **resolved),
            params=resolved,
        )


def deadline_text(state: DueState) -> Text:
    """'in 600 km or 26 days', '450 km overdue', 'today'..."""
    if state.status is DueStatus.OVERDUE:
        km, days = state.overdue_km or 0, state.overdue_days or 0
        if km > 0 and days > 0:
            return Text("deadline.overdue_km_and_days", params={"km": km, "days": days})
        if km > 0:
            return Text("deadline.overdue_km", params={"km": km})
        return Text("deadline.overdue_days", params={"days": days})
    if state.due_reason in ("date", "both") and state.remaining_days == 0:
        return Text("deadline.today")
    if state.due_reason == "mileage":
        return Text("deadline.in_km", params={"km": state.remaining_km})
    if state.due_reason == "date":
        return Text("deadline.in_days", params={"days": state.remaining_days})
    return Text(
        "deadline.in_km_or_days", params={"km": state.remaining_km, "days": state.remaining_days}
    )


def _due_key(prefix: str, source_id: uuid.UUID, state: DueState) -> str:
    return (
        f"{prefix}:{source_id}:{state.next_service_date}:{state.next_service_mileage}:"
        f"{state.status.value}"
    )


def schedule_alert(
    schedule: MaintenanceSchedule, state: DueState, vehicle: Vehicle
) -> DesiredAlert | None:
    priority = DUE_PRIORITY.get(state.status)
    if priority is None:
        return None
    maintenance_type = schedule.maintenance_type
    is_inspection = maintenance_type.code == "vehicle_inspection"
    return DesiredAlert(
        source_type=AlertSource.MAINTENANCE_SCHEDULE,
        source_id=schedule.id,
        alert_type=AlertType.INSPECTION_DUE if is_inspection else AlertType.MAINTENANCE_DUE,
        priority=priority,
        dedup_key=_due_key(AlertSource.MAINTENANCE_SCHEDULE.value, schedule.id, state),
        template=f"alert.maintenance.{state.status.value}",
        params={
            "type_code": maintenance_type.code,
            "type_name": Text(
                f"maintenance_type.{maintenance_type.code}" if maintenance_type.is_system else None,
                maintenance_type.name,
            ),
            "vehicle": vehicle.display_name,
            "deadline": deadline_text(state),
            "next_date": state.next_service_date,
            "next_mileage": state.next_service_mileage,
            "remaining_km": state.remaining_km,
            "remaining_days": state.remaining_days,
        },
        trigger_date=state.next_service_date,
        trigger_mileage=state.next_service_mileage,
    )


def part_alert(part: PartReplacement, state: DueState, vehicle: Vehicle) -> DesiredAlert | None:
    if not state.status.is_at_least(DueStatus.DUE_SOON):
        return None
    return DesiredAlert(
        source_type=AlertSource.PART_REPLACEMENT,
        source_id=part.id,
        alert_type=AlertType.PART_LIFETIME,
        priority=DUE_PRIORITY[state.status],
        dedup_key=_due_key(AlertSource.PART_REPLACEMENT.value, part.id, state),
        template=f"alert.part.{state.status.value}",
        params={
            "part_name": part.part_name,
            "vehicle": vehicle.display_name,
            "deadline": deadline_text(state),
            "next_date": state.next_service_date,
            "next_mileage": state.next_service_mileage,
        },
        trigger_date=state.next_service_date,
        trigger_mileage=state.next_service_mileage,
    )


def _document_priority(days_left: int) -> AlertPriority:
    if days_left < 0:
        return AlertPriority.CRITICAL
    if days_left <= 7:
        return AlertPriority.HIGH
    if days_left <= 30:
        return AlertPriority.MEDIUM
    return AlertPriority.LOW


def document_alert(document: VehicleDocument, vehicle: Vehicle, today: date) -> DesiredAlert | None:
    state = document_state(document.expiration_date, document.reminder_days, today)
    if state.days_until_expiration is None:
        return None
    if state.status is DocumentStatus.EXPIRED:
        step, template = "expired", "alert.document.expired"
    elif state.active_reminder is not None:
        step = str(state.active_reminder)
        template = (
            "alert.document.expires_today"
            if state.days_until_expiration == 0
            else "alert.document.expiring"
        )
    else:
        return None
    return DesiredAlert(
        source_type=AlertSource.VEHICLE_DOCUMENT,
        source_id=document.id,
        alert_type=DOCUMENT_ALERT_TYPES.get(document.document_type, AlertType.DOCUMENT_EXPIRATION),
        priority=_document_priority(state.days_until_expiration),
        dedup_key=f"vehicle_document:{document.id}:{document.expiration_date}:{step}",
        template=template,
        params={
            "title": document.title,
            "document_type": Text(
                f"document_type.{document.document_type.value}", document.document_type.value
            ),
            "vehicle": vehicle.display_name,
            "expiration_date": document.expiration_date,
            "days": abs(state.days_until_expiration),
        },
        trigger_date=document.expiration_date,
    )


def mileage_alert(vehicle: Vehicle, last_reading: date | None, today: date) -> DesiredAlert | None:
    """Ask for a fresh odometer reading when the last one is more than 30 days old."""
    if last_reading is None or today - last_reading <= timedelta(days=MILEAGE_STALE_DAYS):
        return None
    return DesiredAlert(
        source_type=AlertSource.VEHICLE,
        source_id=vehicle.id,
        alert_type=AlertType.MILEAGE_REMINDER,
        priority=AlertPriority.INFO,
        dedup_key=f"vehicle:{vehicle.id}:mileage_stale:{last_reading}",
        template="alert.mileage.stale",
        params={"vehicle": vehicle.display_name, "last_date": last_reading},
    )
