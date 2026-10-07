"""Version 1 API router: mounts every module router under `/api/v1`."""

from fastapi import APIRouter

from app.api import health
from app.modules.alerts.reminders_router import router as reminders_router
from app.modules.alerts.router import router as alerts_router
from app.modules.attachments.router import router as attachments_router
from app.modules.auth.router import router as auth_router
from app.modules.dashboard.router import router as dashboard_router
from app.modules.documents.router import router as documents_router
from app.modules.expenses.router import router as expenses_router
from app.modules.fuel.router import router as fuel_router
from app.modules.garages.router import router as garages_router
from app.modules.maintenance.oil_changes_router import router as oil_changes_router
from app.modules.maintenance.router import router as maintenance_router
from app.modules.maintenance.schedules_router import router as schedules_router
from app.modules.maintenance.types_router import router as maintenance_types_router
from app.modules.mileage.router import router as mileage_router
from app.modules.notes.router import router as notes_router
from app.modules.notifications.router import router as notifications_router
from app.modules.parts.router import router as parts_router
from app.modules.parts.types_router import router as part_types_router
from app.modules.statistics.router import router as statistics_router
from app.modules.timeline.router import router as timeline_router
from app.modules.tires.router import router as tires_router
from app.modules.users.router import router as users_router
from app.modules.vehicles.router import router as vehicles_router
from app.modules.vehicles.sharing_router import router as sharing_router

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(notifications_router)
api_router.include_router(vehicles_router)
api_router.include_router(sharing_router)
api_router.include_router(mileage_router)
api_router.include_router(garages_router)
api_router.include_router(maintenance_types_router)
api_router.include_router(maintenance_router)
api_router.include_router(schedules_router)
api_router.include_router(oil_changes_router)
api_router.include_router(part_types_router)
api_router.include_router(parts_router)
api_router.include_router(documents_router)
api_router.include_router(expenses_router)
api_router.include_router(fuel_router)
api_router.include_router(tires_router)
api_router.include_router(alerts_router)
api_router.include_router(reminders_router)
api_router.include_router(timeline_router)
api_router.include_router(statistics_router)
api_router.include_router(dashboard_router)
api_router.include_router(attachments_router)
api_router.include_router(notes_router)
