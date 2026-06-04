import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user as get_current_user_dep
from app.database.connection import get_db_session
from app.models.user import User
from app.schemas.social_feature_schema import (
    CloseFriendCreate,
    MutualFriend,
    PollCreate,
    PollResponse,
    PollVote,
    ShortVideoCreate,
    ShortVideoResponse,
    StoryCreate,
    StoryResponse,
    SuggestedUser,
    VerificationRequestCreate,
)
from app.services.social_feature_service import SocialFeatureService

router = APIRouter(tags=["social"])


@router.get("/suggested-users", response_model=list[SuggestedUser])
async def suggested_users(
    limit: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict[str, object]]:
    return await SocialFeatureService.suggested_users(session, current_user.id, limit)


@router.get("/mutual-friends/{user_id}", response_model=list[MutualFriend])
async def mutual_friends(
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    return await SocialFeatureService.mutual_friends(session, current_user.id, user_id)


@router.post("/close-friends", status_code=status.HTTP_201_CREATED)
async def add_close_friend(
    payload: CloseFriendCreate,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    try:
        row = await SocialFeatureService.add_close_friend(session, current_user.id, payload.friend_id)
        return {"id": str(row.id), "status": "added"}
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/close-friends/{friend_id}")
async def remove_close_friend(
    friend_id: uuid.UUID,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    await SocialFeatureService.remove_close_friend(session, current_user.id, friend_id)
    return {"status": "removed"}


@router.post("/polls", response_model=PollResponse, status_code=status.HTTP_201_CREATED)
async def create_poll(
    payload: PollCreate,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> PollResponse:
    try:
        poll = await SocialFeatureService.create_poll(session, current_user.id, payload.question, payload.options, payload.expires_at)
        return PollResponse.model_validate({**poll.__dict__, "votes": SocialFeatureService.poll_counts(poll)})
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/polls/{poll_id}/vote", response_model=PollResponse)
async def vote_poll(
    poll_id: uuid.UUID,
    payload: PollVote,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> PollResponse:
    try:
        poll = await SocialFeatureService.vote_poll(session, poll_id, current_user.id, payload.option)
        return PollResponse.model_validate({**poll.__dict__, "votes": SocialFeatureService.poll_counts(poll)})
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/stories", response_model=StoryResponse, status_code=status.HTTP_201_CREATED)
async def create_story(
    payload: StoryCreate,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    return await SocialFeatureService.create_story(session, current_user.id, payload.media_url, payload.caption, payload.audience)


@router.get("/stories", response_model=list[StoryResponse])
async def stories(
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    return await SocialFeatureService.stories(session, current_user.id, limit)


@router.post("/reels", response_model=ShortVideoResponse, status_code=status.HTTP_201_CREATED)
async def create_reel(
    payload: ShortVideoCreate,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    return await SocialFeatureService.create_short_video(session, current_user.id, **payload.model_dump())


@router.get("/reels", response_model=list[ShortVideoResponse])
async def reels(
    limit: int = Query(default=30, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
):
    return await SocialFeatureService.reels(session, limit)


@router.post("/verification-requests", status_code=status.HTTP_201_CREATED)
async def request_verification(
    payload: VerificationRequestCreate,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    row = await SocialFeatureService.request_verification(session, current_user.id, payload.reason, payload.evidence)
    return {"id": str(row.id), "status": row.status}
