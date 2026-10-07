"""Notification preference endpoints."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.api.deps import CurrentUser, DbSession
from app.api.openapi import AUTHENTICATED_ERRORS
from app.core.responses import ApiResponse, success
from app.modules.notifications.schemas import PreferenceResponse, PreferencesUpdate
from app.modules.notifications.service import PreferenceService

router = APIRouter(
    prefix="/users/me/notification-preferences",
    tags=["Notifications"],
    responses=AUTHENTICATED_ERRORS,
)


def get_preference_service(session: DbSession) -> PreferenceService:
    return PreferenceService(session)


PreferenceServiceDep = Annotated[PreferenceService, Depends(get_preference_service)]


@router.get(
    "",
    response_model=ApiResponse[list[PreferenceResponse]],
    summary="My notification preferences",
    description=(
        "One general rule per channel (in_app, email, push, sms), then overrides per alert "
        "type. Defaults: everything in the app, high and critical alerts by e-mail, push and "
        "SMS off."
    ),
)
async def get_preferences(user: CurrentUser, service: PreferenceServiceDep) -> Any:
    return success(await service.effective(user.id))


@router.put(
    "",
    response_model=ApiResponse[list[PreferenceResponse]],
    summary="Replace my notification preferences",
    description="Rules not sent fall back to the defaults.",
)
async def replace_preferences(
    body: PreferencesUpdate, user: CurrentUser, service: PreferenceServiceDep
) -> Any:
    return success(await service.replace(user.id, body))
