"""Alert inbox use cases (listing and status changes)."""

import uuid
from dataclasses import dataclass

from sqlalchemy import ColumnElement, case, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock
from app.core.exceptions import NotFoundError
from app.core.pagination import Page, PageParams, apply_sort, paginate
from app.modules.alerts.models import (
    OPEN_STATUSES,
    Alert,
    AlertPriority,
    AlertStatus,
    AlertType,
)
from app.modules.alerts.schemas import AlertSummary

PRIORITY_RANK = case(
    {priority.value: priority.rank for priority in AlertPriority}, value=Alert.priority
)
ALERT_SORT_FIELDS = {
    "created_at": Alert.created_at,
    "priority": PRIORITY_RANK,
    "trigger_date": Alert.trigger_date,
}


@dataclass(frozen=True, slots=True)
class AlertFilters:
    vehicle_id: uuid.UUID | None = None
    status: list[AlertStatus] | None = None
    priority: list[AlertPriority] | None = None
    alert_type: list[AlertType] | None = None
    sort: str | None = None


class AlertService:
    def __init__(self, session: AsyncSession, clock: Clock) -> None:
        self.session = session
        self.clock = clock

    def _scope(self, user_id: uuid.UUID, vehicle_id: uuid.UUID | None) -> ColumnElement[bool]:
        clause: ColumnElement[bool] = Alert.user_id == user_id
        if vehicle_id is not None:
            clause = clause & (Alert.vehicle_id == vehicle_id)
        return clause

    async def list_alerts(
        self, user_id: uuid.UUID, filters: AlertFilters, params: PageParams
    ) -> Page[Alert]:
        stmt = select(Alert).where(self._scope(user_id, filters.vehicle_id))
        if filters.status:
            stmt = stmt.where(Alert.status.in_(filters.status))
        if filters.priority:
            stmt = stmt.where(Alert.priority.in_(filters.priority))
        if filters.alert_type:
            stmt = stmt.where(Alert.alert_type.in_(filters.alert_type))
        stmt = apply_sort(stmt, filters.sort, ALERT_SORT_FIELDS, "-created_at", Alert.id)
        return await paginate(self.session, stmt, params)

    async def summary(
        self, user_id: uuid.UUID, vehicle_id: uuid.UUID | None = None
    ) -> AlertSummary:
        rows = (
            await self.session.execute(
                select(Alert.priority, Alert.status, func.count())
                .where(self._scope(user_id, vehicle_id), Alert.status.in_(OPEN_STATUSES))
                .group_by(Alert.priority, Alert.status)
            )
        ).all()
        by_priority = dict.fromkeys(AlertPriority, 0)
        unread = 0
        for priority, status, count in rows:
            by_priority[priority] += count
            if status is AlertStatus.ACTIVE:
                unread += count
        return AlertSummary(open=sum(by_priority.values()), unread=unread, by_priority=by_priority)

    async def get(self, user_id: uuid.UUID, alert_id: uuid.UUID) -> Alert:
        alert = await self.session.scalar(
            select(Alert).where(Alert.id == alert_id, Alert.user_id == user_id)
        )
        if alert is None:
            raise NotFoundError("Alert")
        return alert

    async def set_status(self, user_id: uuid.UUID, alert_id: uuid.UUID, status: str) -> Alert:
        alert = await self.get(user_id, alert_id)
        target = AlertStatus(status)
        now = self.clock.now()
        alert.status = target
        if target is AlertStatus.ACTIVE:
            alert.read_at = None
        else:
            alert.read_at = alert.read_at or now
        if target is AlertStatus.DISMISSED:
            alert.dismissed_at = now
        if target is AlertStatus.RESOLVED:
            alert.resolved_at = now
        await self.session.commit()
        return alert

    async def mark_all_read(self, user_id: uuid.UUID, vehicle_id: uuid.UUID | None = None) -> int:
        result = await self.session.execute(
            update(Alert)
            .where(self._scope(user_id, vehicle_id), Alert.status == AlertStatus.ACTIVE)
            .values(status=AlertStatus.READ, read_at=self.clock.now())
        )
        await self.session.commit()
        return int(result.rowcount)  # type: ignore[attr-defined]
