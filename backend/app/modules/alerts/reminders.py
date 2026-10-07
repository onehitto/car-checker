"""Custom reminder use cases."""

import uuid
from collections.abc import Sequence

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock
from app.core.exceptions import NotFoundError, ValidationAppError
from app.modules.alerts.engine import AlertEngine
from app.modules.alerts.models import Reminder
from app.modules.alerts.reminder_state import evaluate_reminder
from app.modules.alerts.schemas import ReminderCreate, ReminderResponse, ReminderUpdate
from app.modules.vehicles.access import VehicleContext

REQUIRED_FIELDS = frozenset({"title", "warning_before_days", "warning_before_km"})


class ReminderService:
    def __init__(self, session: AsyncSession, clock: Clock) -> None:
        self.session = session
        self.clock = clock
        self.alerts = AlertEngine(session, clock)

    def to_response(self, ctx: VehicleContext, reminder: Reminder) -> ReminderResponse:
        response = ReminderResponse.model_validate(reminder)
        if reminder.completed_at is not None:
            return response
        state = evaluate_reminder(
            reminder, ctx.vehicle.current_mileage, self.clock.today(ctx.user.timezone)
        )
        return response.model_copy(
            update={
                "status": state.status,
                "remaining_km": state.remaining_km,
                "remaining_days": state.remaining_days,
            }
        )

    async def list_reminders(
        self, ctx: VehicleContext, completed: bool | None
    ) -> Sequence[Reminder]:
        stmt = select(Reminder).where(Reminder.vehicle_id == ctx.vehicle_id)
        if completed is True:
            stmt = stmt.where(Reminder.completed_at.is_not(None))
        elif completed is False:
            stmt = stmt.where(Reminder.completed_at.is_(None))
        stmt = stmt.order_by(
            Reminder.completed_at.desc().nulls_first(),
            Reminder.due_date.asc().nulls_last(),
            Reminder.due_mileage.asc().nulls_last(),
        )
        return (await self.session.scalars(stmt)).all()

    async def get(self, ctx: VehicleContext, reminder_id: uuid.UUID) -> Reminder:
        reminder = await self.session.scalar(
            select(Reminder).where(
                Reminder.id == reminder_id, Reminder.vehicle_id == ctx.vehicle_id
            )
        )
        if reminder is None:
            raise NotFoundError("Reminder")
        return reminder

    async def create(self, ctx: VehicleContext, data: ReminderCreate) -> Reminder:
        reminder = Reminder(
            **data.model_dump(), vehicle_id=ctx.vehicle_id, created_by_id=ctx.user.id
        )
        self.session.add(reminder)
        await self.alerts.sync_vehicle(ctx.vehicle_id)
        await self.session.commit()
        return reminder

    async def update(
        self, ctx: VehicleContext, reminder_id: uuid.UUID, data: ReminderUpdate
    ) -> Reminder:
        reminder = await self.get(ctx, reminder_id)
        changes = data.model_dump(exclude_unset=True)
        completed = changes.pop("completed", None)
        null_fields = {
            field: "This field cannot be null."
            for field, value in changes.items()
            if value is None and field in REQUIRED_FIELDS
        }
        if null_fields:
            raise ValidationAppError(fields=null_fields)
        for field, value in changes.items():
            setattr(reminder, field, value)
        if reminder.due_date is None and reminder.due_mileage is None:
            raise ValidationAppError(fields={"due_date": "Set due_date and/or due_mileage."})
        if completed is not None:
            reminder.completed_at = self.clock.now() if completed else None
        await self.alerts.sync_vehicle(ctx.vehicle_id)
        await self.session.commit()
        return reminder

    async def delete(self, ctx: VehicleContext, reminder_id: uuid.UUID) -> None:
        result = await self.session.execute(
            delete(Reminder).where(
                Reminder.id == reminder_id, Reminder.vehicle_id == ctx.vehicle_id
            )
        )
        if result.rowcount == 0:  # type: ignore[attr-defined]
            raise NotFoundError("Reminder")
        await self.alerts.sync_vehicle(ctx.vehicle_id)
        await self.session.commit()
