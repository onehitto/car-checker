"""Part type catalog endpoints."""

from app.api.catalog import build_catalog_router
from app.modules.parts.models import PartCategory, PartType
from app.modules.parts.schemas import PartTypeCreate, PartTypeResponse, PartTypeUpdate

router = build_catalog_router(
    prefix="/part-types",
    tag="Part types",
    model=PartType,
    resource="Part type",
    category_enum=PartCategory,
    create_schema=PartTypeCreate,
    update_schema=PartTypeUpdate,
    response_schema=PartTypeResponse,
)
