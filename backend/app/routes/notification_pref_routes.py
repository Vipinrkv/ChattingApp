import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user as get_current_user_dep
from app.database.connection import get_db_session
from app.schemas.notification_pref_schema import (
    NotificationPreferencesResponse,
    NotificationPreferencesUpdate,
)
from app.services.notification_pref_service import NotificationPrefService

router = APIRouter(
    tags=["notification_preferences"],
    dependencies=[Depends(get_current_user_dep)],
)


@router.get("", response_model=NotificationPreferencesResponse)
async def get_preferences(
    current_user=Depends(get_current_user_dep), session: AsyncSession = Depends(get_db_session)
) -> NotificationPreferencesResponse:
    prefs = await NotificationPrefService.get_preferences(session, str(current_user.id))
    return NotificationPreferencesResponse(preferences=prefs)


@router.patch("", response_model=NotificationPreferencesResponse)
async def update_preferences(
    payload: NotificationPreferencesUpdate,
    current_user=Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> NotificationPreferencesResponse:
    try:
        prefs = await NotificationPrefService.set_preferences(session, str(current_user.id), payload.preferences)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    return NotificationPreferencesResponse(preferences=prefs)
