"""Notification preference DTOs."""

from typing import Self

from pydantic import Field, field_validator, model_validator

from app.core.schemas import RequestModel, ResponseModel
from app.modules.alerts.models import AlertPriority, AlertType
from app.modules.notifications.models import ALL_ALERT_TYPES, NotificationChannel

_ALERT_TYPES = {ALL_ALERT_TYPES, *(alert_type.value for alert_type in AlertType)}


class PreferenceItem(RequestModel):
    channel: NotificationChannel
    alert_type: str = Field(
        default=ALL_ALERT_TYPES, description="`all` or one alert type (overrides `all`)."
    )
    enabled: bool = True
    min_priority: AlertPriority = AlertPriority.LOW

    @field_validator("alert_type")
    @classmethod
    def _known_type(cls, value: str) -> str:
        if value not in _ALERT_TYPES:
            raise ValueError(f"Unknown alert type. Use one of: {', '.join(sorted(_ALERT_TYPES))}.")
        return value


class PreferencesUpdate(RequestModel):
    preferences: list[PreferenceItem] = Field(max_length=50)

    @model_validator(mode="after")
    def _unique(self) -> Self:
        keys = [(item.channel, item.alert_type) for item in self.preferences]
        if len(keys) != len(set(keys)):
            raise ValueError("Each channel and alert type pair can appear only once.")
        return self


class PreferenceResponse(ResponseModel):
    channel: NotificationChannel
    alert_type: str
    enabled: bool
    min_priority: AlertPriority
    is_default: bool = Field(description="True when no preference is stored for this rule.")
