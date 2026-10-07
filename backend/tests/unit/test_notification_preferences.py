from app.modules.alerts.models import AlertPriority, AlertType
from app.modules.notifications.models import NotificationChannel
from app.modules.notifications.preferences import StoredPreference, resolve_rule

EMAIL = NotificationChannel.EMAIL


def test_defaults() -> None:
    rule = resolve_rule([], EMAIL, AlertType.MAINTENANCE_DUE)
    assert rule.accepts(AlertPriority.HIGH)
    assert not rule.accepts(AlertPriority.MEDIUM)
    assert not resolve_rule([], NotificationChannel.PUSH, AlertType.MAINTENANCE_DUE).accepts(
        AlertPriority.CRITICAL
    )


def test_specific_type_overrides_all() -> None:
    preferences = [
        StoredPreference(EMAIL, "all", True, AlertPriority.LOW),
        StoredPreference(EMAIL, "mileage_reminder", False, AlertPriority.LOW),
    ]
    assert resolve_rule(preferences, EMAIL, AlertType.MAINTENANCE_DUE).accepts(AlertPriority.LOW)
    assert not resolve_rule(preferences, EMAIL, AlertType.MILEAGE_REMINDER).accepts(
        AlertPriority.CRITICAL
    )


def test_other_channels_are_ignored() -> None:
    preferences = [StoredPreference(NotificationChannel.SMS, "all", True, AlertPriority.INFO)]
    assert not resolve_rule(preferences, EMAIL, AlertType.SYSTEM).accepts(AlertPriority.LOW)
