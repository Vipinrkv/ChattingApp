from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.auth import get_current_user as get_current_user_dep
from app.database.connection import get_db_session
from app.models.user import User
from app.schemas.user_feed_control_schema import UserFeedControlResponse, UserFeedControlUpdate
from app.services.user_feed_control_service import UserFeedControlService

router = APIRouter(
    prefix="/api/v1/posts/controls",
    tags=["posts"],
    dependencies=[Depends(get_current_user_dep)],
)


@router.get("", response_model=UserFeedControlResponse)
async def get_user_feed_settings(
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> UserFeedControlResponse:
    return await UserFeedControlService.get_controls(session, current_user.id)


@router.put("", response_model=UserFeedControlResponse)
async def update_user_feed_settings(
    payload: UserFeedControlUpdate,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> UserFeedControlResponse:
    return await UserFeedControlService.update_controls(session, current_user.id, payload)
