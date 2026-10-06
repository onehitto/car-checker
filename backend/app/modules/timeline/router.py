"""Vehicle timeline endpoint."""

import uuid
from dataclasses import asdict
from datetime import date
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Query
from pydantic import Field

from app.api.deps import DbSession
from app.api.openapi import VEHICLE_ERRORS
from app.core.pagination import PageDep, paginated
from app.core.responses import PaginatedResponse
from app.core.schemas import ResponseModel
from app.modules.timeline.service import TimelineEventType, TimelineFilters, TimelineService
from app.modules.vehicles.access import VehicleViewer

router = APIRouter(tags=["Timeline"], responses=VEHICLE_ERRORS)


class TimelineEventResponse(ResponseModel):
    type: TimelineEventType
    id: uuid.UUID = Field(description="Id of the underlying record (use with its endpoint).")
    date: date
    mileage: int | None
    title: str
    amount: Decimal | None
    currency: str
    subtype: str | None = Field(
        description=(
            "Maintenance type code, expense category, document type, part position or "
            "mileage source, depending on `type`."
        )
    )


@router.get(
    "/vehicles/{vehicle_id}/timeline",
    response_model=PaginatedResponse[TimelineEventResponse],
    summary="Chronological history of a vehicle",
    description=(
        "Mileage readings, maintenance, repairs, part replacements, expenses and document "
        "issues, most recent first. Expenses created by a maintenance or a part are not "
        "repeated."
    ),
)
async def vehicle_timeline(
    ctx: VehicleViewer,
    session: DbSession,
    page: PageDep,
    types: Annotated[list[TimelineEventType] | None, Query(alias="type")] = None,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
) -> Any:
    filters = TimelineFilters(types=types, date_from=date_from, date_to=date_to)
    events = await TimelineService(session).events(ctx.vehicle_id, filters, page)
    currency = ctx.vehicle.currency
    return paginated(events.map(lambda event: {**asdict(event), "currency": currency}))
