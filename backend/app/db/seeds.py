"""Reference data (system catalogs). Idempotent: rows are upserted by their `code`.

Run on every deployment after migrations: `python -m app.cli seed`.
"""

from dataclasses import dataclass

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ids import uuid7
from app.modules.maintenance.models import MaintenanceCategory, MaintenanceType


@dataclass(frozen=True, slots=True)
class CatalogSeed:
    code: str
    name: str
    category: str
    interval_km: int | None = None
    interval_months: int | None = None


# Generic defaults only: users override intervals per vehicle in maintenance schedules.
MAINTENANCE_TYPES: tuple[CatalogSeed, ...] = (
    CatalogSeed("oil_change", "Oil change", "engine", 10_000, 12),
    CatalogSeed("oil_filter", "Oil filter replacement", "filters", 10_000, 12),
    CatalogSeed("air_filter", "Air filter replacement", "filters", 30_000, 24),
    CatalogSeed("cabin_filter", "Cabin filter replacement", "filters", 15_000, 12),
    CatalogSeed("fuel_filter", "Fuel filter replacement", "filters", 60_000, 48),
    CatalogSeed("brake_pads", "Brake pads", "brakes", 40_000),
    CatalogSeed("brake_discs", "Brake discs", "brakes", 80_000),
    CatalogSeed("brake_fluid", "Brake fluid", "fluids", None, 24),
    CatalogSeed("coolant", "Coolant", "fluids", 100_000, 60),
    CatalogSeed("transmission_oil", "Transmission oil", "transmission", 60_000, 48),
    CatalogSeed("timing_belt", "Timing belt", "engine", 100_000, 60),
    CatalogSeed("timing_chain", "Timing chain inspection", "engine", 150_000),
    CatalogSeed("spark_plugs", "Spark plugs", "engine", 40_000, 48),
    CatalogSeed("battery", "Battery", "electrical", None, 48),
    CatalogSeed("tires", "Tires", "tires", 40_000, 60),
    CatalogSeed("suspension", "Suspension", "suspension"),
    CatalogSeed("clutch", "Clutch", "transmission"),
    CatalogSeed("air_conditioning", "Air conditioning service", "climate", None, 24),
    CatalogSeed("wheel_alignment", "Wheel alignment", "tires", 20_000, 12),
    CatalogSeed("vehicle_inspection", "Vehicle inspection", "inspection", None, 12),
    CatalogSeed("repair", "General repair", "repair"),
    CatalogSeed("custom", "Other maintenance", "other"),
)


async def seed_maintenance_types(session: AsyncSession) -> int:
    for seed in MAINTENANCE_TYPES:
        stmt = insert(MaintenanceType).values(
            id=uuid7(),
            code=seed.code,
            name=seed.name,
            category=MaintenanceCategory(seed.category),
            default_interval_km=seed.interval_km,
            default_interval_months=seed.interval_months,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[MaintenanceType.code],
            index_where=MaintenanceType.user_id.is_(None),
            set_={
                "name": stmt.excluded.name,
                "category": stmt.excluded.category,
                "default_interval_km": stmt.excluded.default_interval_km,
                "default_interval_months": stmt.excluded.default_interval_months,
                "updated_at": func.now(),
            },
        )
        await session.execute(stmt)
    return len(MAINTENANCE_TYPES)


async def seed_reference_data(session: AsyncSession) -> dict[str, int]:
    """Upsert every system catalog. The caller commits."""
    return {"maintenance_types": await seed_maintenance_types(session)}
