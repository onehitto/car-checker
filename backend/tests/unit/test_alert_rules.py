"""Alert rules are pure: they are tested with plain model instances (no database)."""

import uuid
from datetime import date

import pytest

from app.core.i18n import Language
from app.modules.alerts.models import AlertPriority, AlertType
from app.modules.alerts.rules import (
    deadline_text,
    document_alert,
    mileage_alert,
    part_alert,
    schedule_alert,
)
from app.modules.documents.models import DocumentType, VehicleDocument
from app.modules.maintenance.calculator import DueState, DueStatus
from app.modules.maintenance.models import MaintenanceCategory, MaintenanceSchedule, MaintenanceType
from app.modules.parts.models import PartReplacement
from app.modules.vehicles.models import FuelType, Vehicle

TODAY = date(2026, 10, 6)
VEHICLE = Vehicle(
    brand="Dacia",
    model="Logan",
    year=2019,
    fuel_type=FuelType.DIESEL,
    currency="EUR",
    current_mileage=59_400,
)


def state(status: DueStatus, **values: object) -> DueState:
    defaults: dict[str, object] = {
        "next_service_date": date(2026, 11, 1),
        "next_service_mileage": 60_000,
        "remaining_km": 600,
        "remaining_days": 26,
        "overdue_km": 0,
        "overdue_days": 0,
        "status": status,
        "due_reason": "both",
    }
    return DueState(**{**defaults, **values})  # type: ignore[arg-type]


def oil_schedule(code: str = "oil_change") -> MaintenanceSchedule:
    schedule = MaintenanceSchedule(vehicle_id=VEHICLE.id, maintenance_type_id=uuid.uuid4())
    schedule.maintenance_type = MaintenanceType(
        code=code, name="Oil change", category=MaintenanceCategory.ENGINE
    )
    return schedule


class TestDeadline:
    @pytest.mark.parametrize(
        ("values", "expected"),
        [
            ({"due_reason": "both"}, "in 600 km or 26 days"),
            ({"due_reason": "mileage"}, "in 600 km"),
            ({"due_reason": "date"}, "in 26 days"),
            ({"due_reason": "date", "remaining_days": 0, "status": DueStatus.DUE}, "today"),
            ({"status": DueStatus.OVERDUE, "overdue_km": 450, "overdue_days": 0}, "450 km overdue"),
            ({"status": DueStatus.OVERDUE, "overdue_km": 0, "overdue_days": 3}, "3 days overdue"),
            (
                {"status": DueStatus.OVERDUE, "overdue_km": 5, "overdue_days": 3},
                "5 km and 3 days overdue",
            ),
        ],
    )
    def test_phrases(self, values: dict[str, object], expected: str) -> None:
        status = values.pop("status", DueStatus.DUE_SOON)
        text = deadline_text(state(status, **values))  # type: ignore[arg-type]
        assert text.resolve(Language.EN) == expected


class TestScheduleAlert:
    def test_no_alert_when_ok_or_unknown(self) -> None:
        assert schedule_alert(oil_schedule(), state(DueStatus.OK), VEHICLE) is None
        assert schedule_alert(oil_schedule(), state(DueStatus.UNKNOWN), VEHICLE) is None

    @pytest.mark.parametrize(
        ("status", "priority"),
        [
            (DueStatus.UPCOMING, AlertPriority.LOW),
            (DueStatus.DUE_SOON, AlertPriority.MEDIUM),
            (DueStatus.DUE, AlertPriority.HIGH),
            (DueStatus.OVERDUE, AlertPriority.CRITICAL),
        ],
    )
    def test_priority_follows_status(self, status: DueStatus, priority: AlertPriority) -> None:
        alert = schedule_alert(oil_schedule(), state(status), VEHICLE)
        assert alert is not None
        assert alert.priority is priority
        assert alert.dedup_key.endswith(f":2026-11-01:60000:{status.value}")

    def test_rendering_in_each_language(self) -> None:
        alert = schedule_alert(oil_schedule(), state(DueStatus.DUE_SOON), VEHICLE)
        assert alert is not None
        english = alert.render(Language.EN)
        assert english.title == "Oil change due soon"
        assert english.message == "Oil change for Dacia Logan is due in 600 km or 26 days."
        assert english.params["next_date"] == "2026-11-01"
        assert alert.render(Language.FR).title == "Vidange bientôt nécessaire"
        assert "خلال 600 كم" in alert.render(Language.AR).message

    def test_inspection_type(self) -> None:
        alert = schedule_alert(oil_schedule("vehicle_inspection"), state(DueStatus.DUE), VEHICLE)
        assert alert is not None and alert.alert_type is AlertType.INSPECTION_DUE


class TestPartAlert:
    def test_only_from_due_soon(self) -> None:
        part = PartReplacement(part_name="Brake pads", installed_date=date(2024, 1, 1))
        assert part_alert(part, state(DueStatus.UPCOMING), VEHICLE) is None
        alert = part_alert(part, state(DueStatus.OVERDUE, overdue_km=500), VEHICLE)
        assert alert is not None
        assert alert.render(Language.EN).title == "Brake pads past its lifetime"


class TestDocumentAlert:
    def document(
        self, expiration: date | None, doc_type: DocumentType = DocumentType.INSURANCE
    ) -> VehicleDocument:
        return VehicleDocument(
            document_type=doc_type,
            title="AXA 2026",
            expiration_date=expiration,
            reminder_days=[30, 7, 1, 0],
        )

    @pytest.mark.parametrize(
        ("expiration", "step", "priority", "title"),
        [
            (date(2026, 10, 30), "30", AlertPriority.MEDIUM, "AXA 2026 expires in 24 days"),
            (date(2026, 10, 10), "7", AlertPriority.HIGH, "AXA 2026 expires in 4 days"),
            (date(2026, 10, 6), "0", AlertPriority.HIGH, "AXA 2026 expires today"),
            (date(2026, 10, 1), "expired", AlertPriority.CRITICAL, "AXA 2026 has expired"),
        ],
    )
    def test_steps(self, expiration: date, step: str, priority: AlertPriority, title: str) -> None:
        alert = document_alert(self.document(expiration), VEHICLE, TODAY)
        assert alert is not None
        assert alert.dedup_key.endswith(f":{expiration}:{step}")
        assert alert.priority is priority
        assert alert.alert_type is AlertType.INSURANCE_EXPIRATION
        assert alert.render(Language.EN).title == title

    def test_no_alert_before_first_reminder_or_without_expiration(self) -> None:
        assert document_alert(self.document(date(2026, 12, 31)), VEHICLE, TODAY) is None
        assert document_alert(self.document(None), VEHICLE, TODAY) is None

    def test_type_mapping_and_translation(self) -> None:
        alert = document_alert(
            self.document(date(2026, 10, 1), DocumentType.ROAD_TAX), VEHICLE, TODAY
        )
        assert alert is not None and alert.alert_type is AlertType.DOCUMENT_EXPIRATION
        assert alert.render(Language.FR).message.startswith("Vignette « AXA 2026 »")


class TestMileageAlert:
    def test_stale_reading(self) -> None:
        assert mileage_alert(VEHICLE, date(2026, 9, 10), TODAY) is None
        alert = mileage_alert(VEHICLE, date(2026, 9, 1), TODAY)
        assert alert is not None
        assert alert.priority is AlertPriority.INFO
        assert alert.render(Language.EN).title == "Update the mileage of Dacia Logan"
        assert mileage_alert(VEHICLE, None, TODAY) is None
