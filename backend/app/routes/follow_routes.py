# c:\Users\Vipin\OneDrive\Desktop\WebAplications\ChattingApp\backend\app\routes\follow_routes.py
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user as get_current_user_dep
from app.database.connection import get_db_session
from app.models.user import User
from app.schemas.friend_schema import FriendResponse
from app.services.follow_service import (
    FollowError,
    follow_user,
    list_followers,
    list_following,
    unfollow_user,
)

router = APIRouter(
    tags=["follows"],
    dependencies=[Depends(get_current_user_dep)],
)


@router.post("/{following_id}", status_code=status.HTTP_201_CREATED)
async def follow(
    following_id: uuid.UUID,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    current_user_id = current_user.id
    try:
        follower = await follow_user(session, current_user_id, following_id)
        return {
            "follower_id": follower.follower_id,
            "following_id": follower.following_id,
            "created_at": follower.created_at,
        }
    except FollowError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/{following_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unfollow(
    following_id: uuid.UUID,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    current_user_id = current_user.id
    await unfollow_user(session, current_user_id, following_id)


@router.get("/following", response_model=list[FriendResponse])
async def get_following(
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> list[FriendResponse]:
    current_user_id = current_user.id
    return await list_following(session, current_user_id)


@router.get("/followers", response_model=list[FriendResponse])
async def get_followers(
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> list[FriendResponse]:
    current_user_id = current_user.id
    return await list_followers(session, current_user_id)
