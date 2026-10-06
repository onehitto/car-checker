"""Version 1 API router: mounts every module router under `/api/v1`."""

from fastapi import APIRouter

from app.api import health
from app.modules.auth.router import router as auth_router
from app.modules.documents.router import router as documents_router
from app.modules.expenses.router import router as expenses_router
from app.modules.garages.router import router as garages_router
from app.modules.maintenance.router import router as maintenance_router
from app.modules.maintenance.schedules_router import router as schedules_router
from app.modules.maintenance.types_router import router as maintenance_types_router
from app.modules.mileage.router import router as mileage_router
from app.modules.parts.router import router as parts_router
from app.modules.parts.types_router import router as part_types_router
from app.modules.users.router import router as users_router
from app.modules.vehicles.router import router as vehicles_router

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(vehicles_router)
api_router.include_router(mileage_router)
api_router.include_router(garages_router)
api_router.include_router(maintenance_types_router)
api_router.include_router(maintenance_router)
api_router.include_router(schedules_router)
api_router.include_router(part_types_router)
api_router.include_router(parts_router)
api_router.include_router(documents_router)
api_router.include_router(expenses_router)
