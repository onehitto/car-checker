"""Resolution of notification preferences (pure) and defaults."""

from collections.abc import Iterable
from dataclasses import dataclass

from app.modules.alerts.models import AlertPriority, AlertType
from app.modules.notifications.models import ALL_ALERT_TYPES, NotificationChannel


@dataclass(frozen=True, slots=True)
class ChannelRule:
    enabled: bool
    min_priority: AlertPriority

    def accepts(self, priority: AlertPriority) -> bool:
        return self.enabled and priority.rank >= self.min_priority.rank


# Without any stored preference: everything in the app, important alerts by e-mail,
# push and SMS off until the user opts in.
DEFAULT_RULES: dict[NotificationChannel, ChannelRule] = {
    NotificationChannel.IN_APP: ChannelRule(True, AlertPriority.INFO),
    NotificationChannel.EMAIL: ChannelRule(True, AlertPriority.HIGH),
    NotificationChannel.PUSH: ChannelRule(False, AlertPriority.MEDIUM),
    NotificationChannel.SMS: ChannelRule(False, AlertPriority.CRITICAL),
}
EXTERNAL_CHANNELS = (NotificationChannel.EMAIL, NotificationChannel.PUSH, NotificationChannel.SMS)


@dataclass(frozen=True, slots=True)
class StoredPreference:
    channel: NotificationChannel
    alert_type: str
    enabled: bool
    min_priority: AlertPriority


def resolve_rule(
    preferences: Iterable[StoredPreference], channel: NotificationChannel, alert_type: AlertType
) -> ChannelRule:
    """A rule for the alert type wins over the `all` rule, which wins over the default."""
    general: ChannelRule | None = None
    for preference in preferences:
        if preference.channel is not channel:
            continue
        rule = ChannelRule(preference.enabled, preference.min_priority)
        if preference.alert_type == alert_type.value:
            return rule
        if preference.alert_type == ALL_ALERT_TYPES:
            general = rule
    return general or DEFAULT_RULES[channel]
