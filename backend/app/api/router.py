"""Version 1 API router: mounts every module router under `/api/v1`."""

from fastapi import APIRouter

from app.api import health

api_router = APIRouter()
api_router.include_router(health.router)
