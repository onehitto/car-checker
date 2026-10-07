"""Alert engine: reconciles stored alerts with what the rules want right now.

Idempotent. Called synchronously after writes that change deadlines (same transaction, so
the API is immediately consistent) and periodically by the worker for every vehicle,
because time passes without writes. See docs/05-domain-logic.md, section 14.
"""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import and_, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import joinedload

from app.core.clock import Clock
from app.core.ids import uuid7
from app.core.logging import get_logger
from app.modules.alerts.models import (
    OPEN_STATUSES,
    Alert,
    AlertPriority,
    AlertSource,
    AlertStatus,
    AlertType,
    Reminder,
)
from app.modules.alerts.reminder_state import evaluate_reminder
from app.modules.alerts.rules import (
    DesiredAlert,
    document_alert,
    mileage_alert,
    part_alert,
    reminder_alert,
    schedule_alert,
)
from app.modules.documents.models import VehicleDocument
from app.modules.maintenance.models import MaintenanceSchedule
from app.modules.maintenance.schedule_state import evaluate_schedule
from app.modules.mileage.models import MileageEntry
from app.modules.parts.lifetime import evaluate_part
from app.modules.parts.models import PartReplacement
from app.modules.users.models import User
from app.modules.vehicles.models import SharedRole, Vehicle, VehicleAccess, VehicleStatus

logger = get_logger(__name__)

# Alerts of these sources are owned by the engine (created and resolved automatically).
MANAGED_SOURCES = (
    AlertSource.MAINTENANCE_SCHEDULE,
    AlertSource.VEHICLE_DOCUMENT,
    AlertSource.PART_REPLACEMENT,
    AlertSource.VEHICLE,
    AlertSource.REMINDER,
)


@dataclass(frozen=True, slots=True)
class CreatedAlert:
    id: uuid.UUID
    user_id: uuid.UUID
    priority: AlertPriority
    alert_type: AlertType


@dataclass(slots=True)
class SyncResult:
    created: list[CreatedAlert] = field(default_factory=list)
    resolved: int = 0

    def merge(self, other: "SyncResult") -> None:
        self.created.extend(other.created)
        self.resolved += other.resolved


class AlertEngine:
    def __init__(self, session: AsyncSession, clock: Clock) -> None:
        self.session = session
        self.clock = clock

    async def sync_vehicle(self, vehicle_id: uuid.UUID) -> SyncResult:
        """Bring the alerts of one vehicle up to date (no commit)."""
        await self.session.flush()
        vehicle = await self.session.get(Vehicle, vehicle_id)
        if vehicle is None:
            return SyncResult()
        recipients = await self._recipients(vehicle)
        owner = next((user for user in recipients if user.id == vehicle.owner_id), None)
        today = self.clock.today(owner.timezone if owner else "UTC")
        desired = (
            await self.desired_alerts(vehicle, today)
            if vehicle.status is VehicleStatus.ACTIVE
            else []
        )
        return await self._reconcile(vehicle, recipients, desired)

    async def desired_alerts(self, vehicle: Vehicle, today: date) -> list[DesiredAlert]:
        """Every alert the vehicle deserves today, at most one per source."""
        desired: list[DesiredAlert | None] = []

        schedules = await self.session.scalars(
            select(MaintenanceSchedule)
            .options(joinedload(MaintenanceSchedule.maintenance_type))
            .where(MaintenanceSchedule.vehicle_id == vehicle.id, MaintenanceSchedule.enabled)
        )
        for schedule in schedules:
            state = evaluate_schedule(schedule, vehicle.current_mileage, today)
            desired.append(schedule_alert(schedule, state, vehicle))

        documents = await self.session.scalars(
            select(VehicleDocument).where(
                VehicleDocument.vehicle_id == vehicle.id,
                VehicleDocument.expiration_date.is_not(None),
            )
        )
        desired.extend(document_alert(document, vehicle, today) for document in documents)

        parts = await self.session.scalars(
            select(PartReplacement).where(
                PartReplacement.vehicle_id == vehicle.id,
                PartReplacement.removed_date.is_(None),
                or_(
                    PartReplacement.expected_lifetime_km.is_not(None),
                    PartReplacement.expected_lifetime_months.is_not(None),
                ),
            )
        )
        for part in parts:
            part_state = evaluate_part(part, vehicle.current_mileage, today)
            if part_state is not None:
                desired.append(part_alert(part, part_state, vehicle))

        reminders = await self.session.scalars(
            select(Reminder).where(
                Reminder.vehicle_id == vehicle.id, Reminder.completed_at.is_(None)
            )
        )
        for reminder in reminders:
            state = evaluate_reminder(reminder, vehicle.current_mileage, today)
            desired.append(reminder_alert(reminder, state, vehicle))

        last_reading = await self.session.scalar(
            select(func.max(MileageEntry.recorded_on)).where(MileageEntry.vehicle_id == vehicle.id)
        )
        desired.append(mileage_alert(vehicle, last_reading, today))
        return [alert for alert in desired if alert is not None]

    async def _recipients(self, vehicle: Vehicle) -> Sequence[User]:
        """The owner and editors receive alerts; viewers (buyer, mechanic) do not."""
        return (
            await self.session.scalars(
                select(User)
                .outerjoin(
                    VehicleAccess,
                    and_(VehicleAccess.user_id == User.id, VehicleAccess.vehicle_id == vehicle.id),
                )
                .where(
                    User.is_active,
                    or_(User.id == vehicle.owner_id, VehicleAccess.role == SharedRole.EDITOR),
                )
            )
        ).all()

    async def _reconcile(
        self, vehicle: Vehicle, recipients: Sequence[User], desired: list[DesiredAlert]
    ) -> SyncResult:
        result = SyncResult()
        now = self.clock.now()
        wanted = {alert.source: alert for alert in desired}
        recipient_ids = {user.id for user in recipients}

        # 1. Resolve open alerts whose situation changed or disappeared.
        open_alerts = await self.session.scalars(
            select(Alert).where(
                Alert.vehicle_id == vehicle.id,
                Alert.status.in_(OPEN_STATUSES),
                Alert.source_type.in_(MANAGED_SOURCES),
            )
        )
        for alert in open_alerts:
            want = wanted.get((alert.source_type, alert.source_id))  # type: ignore[arg-type]
            if (
                alert.user_id not in recipient_ids
                or want is None
                or want.dedup_key != alert.dedup_key
            ):
                alert.status = AlertStatus.RESOLVED
                alert.resolved_at = now
                result.resolved += 1

        if not desired or not recipients:
            await self.session.flush()
            return result

        # 2. Create the missing ones (a dismissed or resolved alert with the same key is kept).
        existing = set(
            (
                await self.session.execute(
                    select(Alert.user_id, Alert.dedup_key).where(
                        Alert.user_id.in_(recipient_ids),
                        Alert.dedup_key.in_([alert.dedup_key for alert in desired]),
                    )
                )
            ).all()
        )
        rows = []
        for user in recipients:
            for wanted_alert in desired:
                if (user.id, wanted_alert.dedup_key) in existing:
                    continue
                rendered = wanted_alert.render(user.preferred_language)
                rows.append(
                    {
                        "id": uuid7(),
                        "user_id": user.id,
                        "vehicle_id": vehicle.id,
                        "alert_type": wanted_alert.alert_type,
                        "source_type": wanted_alert.source_type,
                        "source_id": wanted_alert.source_id,
                        "dedup_key": wanted_alert.dedup_key,
                        "title": rendered.title,
                        "message": rendered.message,
                        "template_key": wanted_alert.template,
                        "template_params": rendered.params,
                        "priority": wanted_alert.priority,
                        "status": AlertStatus.ACTIVE,
                        "trigger_date": wanted_alert.trigger_date,
                        "trigger_mileage": wanted_alert.trigger_mileage,
                        "created_at": now,
                        "updated_at": now,
                    }
                )
        if rows:
            inserted = await self.session.execute(
                insert(Alert)
                .values(rows)
                .on_conflict_do_nothing(index_elements=[Alert.user_id, Alert.dedup_key])
                .returning(Alert.id, Alert.user_id, Alert.priority, Alert.alert_type)
            )
            result.created = [CreatedAlert(*row) for row in inserted.all()]
        return result


async def sync_all_vehicles(
    session_factory: async_sessionmaker[AsyncSession], clock: Clock, batch_size: int = 100
) -> SyncResult:
    """Refresh the alerts of every vehicle, committing per batch (used by the worker)."""
    total = SyncResult()
    last_id: uuid.UUID | None = None
    while True:
        async with session_factory() as session:
            stmt = select(Vehicle.id).order_by(Vehicle.id).limit(batch_size)
            if last_id is not None:
                stmt = stmt.where(Vehicle.id > last_id)
            vehicle_ids = list((await session.scalars(stmt)).all())
            if not vehicle_ids:
                return total
            engine = AlertEngine(session, clock)
            for vehicle_id in vehicle_ids:
                total.merge(await engine.sync_vehicle(vehicle_id))
            await session.commit()
            last_id = vehicle_ids[-1]
            logger.info("alerts_batch_synced", vehicles=len(vehicle_ids))
