"""Version 1 API router: mounts every module router under `/api/v1`."""

from fastapi import APIRouter

from app.api import health
from app.modules.auth.router import router as auth_router
from app.modules.garages.router import router as garages_router
from app.modules.mileage.router import router as mileage_router
from app.modules.users.router import router as users_router
from app.modules.vehicles.router import router as vehicles_router

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(vehicles_router)
api_router.include_router(mileage_router)
api_router.include_router(garages_router)
