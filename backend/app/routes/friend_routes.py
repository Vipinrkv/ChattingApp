# c:\Users\Vipin\OneDrive\Desktop\WebAplications\ChattingApp\backend\app\routes\friend_routes.py
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user as get_current_user_dep
from app.database.connection import get_db_session
from app.models.user import User
from app.schemas.friend_schema import (
    FriendDecisionRequest,
    FriendRequestResponse,
    FriendResponse,
)
from app.services.friend_service import (
    FriendRequestError,
    list_friends,
    list_pending_friend_requests,
    respond_to_friend_request,
    send_friend_request,
)

router = APIRouter(
    prefix="/friends",
    tags=["friends"],
    dependencies=[Depends(get_current_user_dep)],
)


@router.post(
    "/requests/{addressee_id}",
    response_model=FriendRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_friend_request(
    addressee_id: uuid.UUID,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> FriendRequestResponse:
    current_user_id = current_user.id
    try:
        return await send_friend_request(session, current_user_id, addressee_id)
    except FriendRequestError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post(
    "/requests/{request_id}/respond",
    response_model=FriendRequestResponse,
)
async def respond_friend_request(
    request_id: uuid.UUID,
    payload: FriendDecisionRequest,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> FriendRequestResponse:
    current_user_id = current_user.id
    try:
        return await respond_to_friend_request(
            session,
            current_user_id,
            request_id,
            payload.action,
        )
    except FriendRequestError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("", response_model=list[FriendResponse])
async def get_friends(
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> list[FriendResponse]:
    current_user_id = current_user.id
    return await list_friends(session, current_user_id)


@router.get("/requests", response_model=list[FriendRequestResponse])
async def get_pending_requests(
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> list[FriendRequestResponse]:
    current_user_id = current_user.id
    return await list_pending_friend_requests(session, current_user_id)
