from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user as get_current_user_dep
from app.database.connection import get_db_session
from app.services.notification_service import NotificationService
from app.schemas.notification_schema import NotificationResponse

router = APIRouter()


@router.get("", response_model=list[NotificationResponse])
async def list_notifications(
    current_user=Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
    limit: int = 50,
    offset: int = 0,
):
    notifs = await NotificationService.list_notifications(session, str(current_user.id), limit=limit, offset=offset)
    return notifs


@router.patch("/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    current_user=Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    # Note: For now mark by id; permission checks can be added
    success = await NotificationService.mark_as_read(session, notification_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to mark notification as read")
    return {"ok": True}
