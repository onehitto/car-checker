"""Alert DTOs."""

import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import Field

from app.core.schemas import RequestModel, ResponseModel
from app.modules.alerts.models import AlertPriority, AlertSource, AlertStatus, AlertType


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
