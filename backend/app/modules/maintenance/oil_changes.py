"""Oil changes: maintenance records of the `oil_change` type with oil-specific details.

The parent maintenance record carries date, mileage, costs, garage and notes, so oil changes
take part in maintenance history, schedules, expenses, statistics and the timeline.
"""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock
from app.core.exceptions import NotFoundError
from app.core.pagination import Page, PageParams, paginate
from app.modules.maintenance.models import (
    MaintenanceKind,
    MaintenanceRecord,
    MaintenanceType,
    OilChange,
)
from app.modules.maintenance.records import MaintenanceRecordService, with_relations
from app.modules.maintenance.schemas import (
    OIL_FIELDS,
    MaintenanceRecordCreate,
    MaintenanceRecordResponse,
    MaintenanceRecordUpdate,
    OilChangeCreate,
    OilChangeResponse,
    OilChangeUpdate,
)
from app.modules.vehicles.access import VehicleContext

OIL_CHANGE_CODE = "oil_change"
OIL_FILTER_CODE = "oil_filter"


def to_response(record: MaintenanceRecord, oil: OilChange) -> OilChangeResponse:
    base = MaintenanceRecordResponse.model_validate(record).model_dump()
    details = {field: getattr(oil, field) for field in OIL_FIELDS}
    return OilChangeResponse.model_validate({**base, **details})


class OilChangeService:
    def __init__(self, session: AsyncSession, clock: Clock) -> None:
        self.session = session
        self.records = MaintenanceRecordService(session, clock)

    async def _system_type(self, code: str) -> MaintenanceType:
        maintenance_type = await self.session.scalar(
            select(MaintenanceType).where(
                MaintenanceType.code == code, MaintenanceType.user_id.is_(None)
            )
        )
        if maintenance_type is None:  # reference data missing: seed not run
            raise NotFoundError(message=f"System maintenance type '{code}' is not configured.")
        return maintenance_type

    async def list_oil_changes(
        self, ctx: VehicleContext, params: PageParams
    ) -> Page[OilChangeResponse]:
        stmt = (
            with_relations(select(MaintenanceRecord))
            .join(OilChange, OilChange.maintenance_record_id == MaintenanceRecord.id)
            .where(MaintenanceRecord.vehicle_id == ctx.vehicle_id)
            .order_by(MaintenanceRecord.service_date.desc(), MaintenanceRecord.id.desc())
        )
        page = await paginate(self.session, stmt, params)
        details = {
            oil.maintenance_record_id: oil
            for oil in await self.session.scalars(
                select(OilChange).where(
                    OilChange.maintenance_record_id.in_([r.id for r in page.items])
                )
            )
        }
        return page.map(lambda record: to_response(record, details[record.id]))

    async def _load(
        self, ctx: VehicleContext, record_id: uuid.UUID
    ) -> tuple[MaintenanceRecord, OilChange]:
        oil = await self.session.scalar(
            select(OilChange)
            .join(MaintenanceRecord, MaintenanceRecord.id == OilChange.maintenance_record_id)
            .where(
                OilChange.maintenance_record_id == record_id,
                MaintenanceRecord.vehicle_id == ctx.vehicle_id,
            )
            .execution_options(populate_existing=True)
        )
        if oil is None:
            raise NotFoundError("Oil change")
        return await self.records.get(ctx.vehicle_id, record_id), oil

    async def get(self, ctx: VehicleContext, record_id: uuid.UUID) -> OilChangeResponse:
        return to_response(*await self._load(ctx, record_id))

    async def create(self, ctx: VehicleContext, data: OilChangeCreate) -> OilChangeResponse:
        oil_type = await self._system_type(OIL_CHANGE_CODE)
        values = data.model_dump(exclude=set(OIL_FIELDS))
        record = await self.records.add(
            ctx,
            MaintenanceRecordCreate(
                **values, maintenance_type_id=oil_type.id, kind=MaintenanceKind.MAINTENANCE
            ),
        )
        oil = OilChange(maintenance_record_id=record.id, **data.model_dump(include=set(OIL_FIELDS)))
        self.session.add(oil)
        await self._after_write(ctx, record, oil)
        return await self.get(ctx, record.id)

    async def update(
        self, ctx: VehicleContext, record_id: uuid.UUID, data: OilChangeUpdate
    ) -> OilChangeResponse:
        record, oil = await self._load(ctx, record_id)
        changes = data.model_dump(exclude_unset=True)
        record_changes = {k: v for k, v in changes.items() if k not in OIL_FIELDS}
        if record_changes:
            record = await self.records.change(
                ctx, record.id, MaintenanceRecordUpdate.model_validate(record_changes)
            )
        for field in OIL_FIELDS & changes.keys():
            value: Any = changes[field]
            if field == "oil_filter_changed" and value is None:
                continue
            setattr(oil, field, value)
        await self._after_write(ctx, record, oil)
        return await self.get(ctx, record.id)

    async def delete(self, ctx: VehicleContext, record_id: uuid.UUID) -> None:
        await self._load(ctx, record_id)
        await self.records.delete(ctx, record_id)

    async def _after_write(
        self, ctx: VehicleContext, record: MaintenanceRecord, oil: OilChange
    ) -> None:
        if oil.oil_filter_changed:
            # The filter replaced with the oil also resets the oil filter schedule.
            filter_type = await self._system_type(OIL_FILTER_CODE)
            await self.records.schedules.record_service(
                ctx.vehicle, filter_type.id, record.service_date, record.mileage
            )
        await self.records.alerts.sync_vehicle(ctx.vehicle_id)
        await self.session.commit()
