"""Alert DTOs."""

import uuid
from datetime import date, datetime
from typing import Any, Literal, Self

from pydantic import Field, model_validator

from app.core.schemas import LongText, Mileage, RequestModel, ResponseModel, ShortText
from app.modules.alerts.models import AlertPriority, AlertSource, AlertStatus, AlertType
from app.modules.maintenance.calculator import DueStatus


class AlertResponse(ResponseModel):
    id: uuid.UUID
    vehicle_id: uuid.UUID | None
    alert_type: AlertType
    source_type: AlertSource | None
    source_id: uuid.UUID | None
    title: str = Field(description="Rendered in the recipient's language at creation.")
    message: str
    template_key: str | None = Field(description="i18n key, to re-render in another language.")
    template_params: dict[str, Any]
    priority: AlertPriority
    status: AlertStatus
    trigger_date: date | None = Field(description="Deadline the alert refers to.")
    trigger_mileage: int | None = Field(description="Deadline mileage (km).")
    read_at: datetime | None
    dismissed_at: datetime | None
    resolved_at: datetime | None
    created_at: datetime


class AlertUpdate(RequestModel):
    status: Literal["active", "read", "dismissed", "resolved"] = Field(
        description="`active` marks the alert unread again."
    )


class AlertSummary(ResponseModel):
    open: int = Field(description="Active + read alerts.")
    unread: int = Field(description="Active alerts.")
    by_priority: dict[AlertPriority, int] = Field(description="Open alerts per priority.")


class ReadAllResponse(ResponseModel):
    updated: int


# --- Custom reminders -----------------------------------------------------------------------


class ReminderCreate(RequestModel):
    title: ShortText
    notes: LongText | None = None
    due_date: date | None = None
    due_mileage: Mileage | None = None
    warning_before_days: int = Field(default=7, ge=0, le=365)
    warning_before_km: int = Field(default=500, ge=0, le=100_000)

    @model_validator(mode="after")
    def _has_due(self) -> Self:
        if self.due_date is None and self.due_mileage is None:
            raise ValueError("Set due_date and/or due_mileage.")
        return self


class ReminderUpdate(RequestModel):
    title: ShortText | None = None
    notes: LongText | None = None
    due_date: date | None = None
    due_mileage: Mileage | None = None
    warning_before_days: int | None = Field(default=None, ge=0, le=365)
    warning_before_km: int | None = Field(default=None, ge=0, le=100_000)
    completed: bool | None = Field(default=None, description="Mark done (true) or reopen (false).")


class ReminderResponse(ResponseModel):
    id: uuid.UUID
    vehicle_id: uuid.UUID
    title: str
    notes: str | None
    due_date: date | None
    due_mileage: int | None
    warning_before_days: int
    warning_before_km: int
    completed_at: datetime | None
    status: DueStatus = DueStatus.UNKNOWN
    remaining_km: int | None = None
    remaining_days: int | None = None
    created_by_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
