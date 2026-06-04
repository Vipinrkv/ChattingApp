# c:\Users\Vipin\OneDrive\Desktop\WebAplications\ChattingApp\backend\app\routes\chat_routes.py
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user as get_current_user_dep
from app.core.errors import BadRequestError, ForbiddenError
from app.database.connection import get_db_session
from app.models.user import User
from app.schemas.message_schema import (
    ChatSettingsResponse,
    ChatSettingsUpdateRequest,
    MessageCreateRequest,
    MessageResponse,
)
from app.services.chat_service import (
    ChatError,
    get_conversation,
    mark_message_as_seen,
    send_message,
    serialize_message,
    update_chat_settings,
)

router = APIRouter(
    tags=["chats"],
    dependencies=[Depends(get_current_user_dep)],
)


@router.post("/{receiver_id}/messages", response_model=MessageResponse)
async def create_message(
    receiver_id: uuid.UUID,
    payload: MessageCreateRequest,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    current_user_id = current_user.id
    try:
        message = await send_message(session, current_user_id, receiver_id, payload.content)
        return serialize_message(message)
    except ChatError as exc:
        raise BadRequestError(str(exc), code="chat_message_rejected") from exc


@router.get("/{peer_id}/messages", response_model=list[MessageResponse])
async def list_messages(
    peer_id: uuid.UUID,
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    current_user_id = current_user.id
    try:
        return await get_conversation(session, current_user_id, peer_id, limit)
    except ChatError as exc:
        raise ForbiddenError(str(exc), code="chat_forbidden") from exc


@router.patch("/{peer_id}/settings", response_model=ChatSettingsResponse)
async def patch_chat_settings(
    peer_id: uuid.UUID,
    payload: ChatSettingsUpdateRequest,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> ChatSettingsResponse:
    current_user_id = current_user.id
    try:
        return await update_chat_settings(
            session,
            current_user_id,
            peer_id,
            payload.is_muted,
            payload.is_archived,
        )
    except ChatError as exc:
        raise BadRequestError(str(exc), code="chat_settings_invalid") from exc


@router.patch("/{peer_id}/messages/{message_id}/seen")
async def mark_message_seen_endpoint(
    peer_id: uuid.UUID,
    message_id: uuid.UUID,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    """Mark a message as seen by the current user"""
    current_user_id = current_user.id
    try:
        return await mark_message_as_seen(session, message_id, current_user_id, peer_id)
    except ChatError as exc:
        raise ForbiddenError(str(exc), code="chat_forbidden") from exc
