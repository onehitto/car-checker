"""Maintenance type catalog endpoints."""

from app.api.catalog import build_catalog_router
from app.modules.maintenance.models import MaintenanceCategory, MaintenanceType
from app.modules.maintenance.schemas import (
    MaintenanceTypeCreate,
    MaintenanceTypeResponse,
    MaintenanceTypeUpdate,
)

router = build_catalog_router(
    prefix="/maintenance-types",
    tag="Maintenance types",
    model=MaintenanceType,
    resource="Maintenance type",
    category_enum=MaintenanceCategory,
    create_schema=MaintenanceTypeCreate,
    update_schema=MaintenanceTypeUpdate,
    response_schema=MaintenanceTypeResponse,
)
