# c:\Users\Vipin\OneDrive\Desktop\WebAplications\ChattingApp\backend\app\routes\chat_routes.py
import logging
from datetime import datetime
import uuid

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user as get_current_user_dep
from app.core.errors import BadRequestError, ForbiddenError, InternalServerError
from app.database.connection import get_db_session
from app.models.user import User
from app.schemas.message_schema import (
    ChatSettingsResponse,
    ChatSettingsUpdateRequest,
    MessageForwardRequest,
    MessageCreateRequest,
    MessageReactionRequest,
    MessageResponse,
    MessageUpdateRequest,
)
from app.core.filtering import search_records
from app.core.pagination import parse_cursor
from app.services.chat_service import (
    ChatError,
    delete_message,
    forward_message,
    get_conversation,
    mark_message_as_seen,
    send_message,
    send_media_message,
    serialize_message,
    update_chat_settings,
    update_message,
    toggle_message_reaction,
    toggle_pin_message,
)
from app.services.media_service import MediaError, store_chat_upload
from app.websocket.chat_socket import manager as chat_manager

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["chats"],
    dependencies=[Depends(get_current_user_dep)],
)


def _chat_bad_request(exc: Exception, code: str = "chat_request_invalid") -> BadRequestError:
    return BadRequestError(str(exc), code=code)


def _chat_forbidden(exc: Exception, code: str = "chat_forbidden") -> ForbiddenError:
    return ForbiddenError(str(exc), code=code)


@router.post("/{receiver_id}/messages", response_model=MessageResponse)
async def create_message(
    receiver_id: uuid.UUID,
    payload: MessageCreateRequest,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    current_user_id = current_user.id
    try:
        if payload.media_url:
            media_name = payload.media_name or payload.media_url.split('/')[-1] or 'media'
            message = await send_media_message(
                session,
                current_user_id,
                receiver_id,
                payload.content,
                payload.media_url,
                payload.media_type or 'application/octet-stream',
                media_name,
                payload.media_size or 0,
            )
        else:
            message = await send_message(
                session,
                current_user_id,
                receiver_id,
                payload.content,
                payload.reply_to_message_id,
            )
        return serialize_message(message)
    except ChatError as exc:
        raise _chat_bad_request(exc, code="chat_message_rejected") from exc


@router.post("/{receiver_id}/messages/media", response_model=MessageResponse)
async def create_media_message(
    receiver_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
    caption: str = Form(default=""),
    file: UploadFile = File(...),
) -> dict:
    current_user_id = current_user.id
    try:
        origin = request.headers.get("origin")
    except Exception:
        origin = None
    logger.info("Media upload request: origin=%s path=%s user=%s receiver=%s", origin, request.url.path, current_user_id, receiver_id)
    try:
        media = await store_chat_upload(file)
        message = await send_media_message(
            session,
            current_user_id,
            receiver_id,
            caption.strip(),
            media["url"],
            media["content_type"],
            media["name"],
            media["size"],
        )

        response = serialize_message(message)

        # Broadcast to both websocket participants (if connected).
        try:
            await chat_manager.send_to_user(current_user_id, {"type": "message", "data": response})
            await chat_manager.send_to_user(receiver_id, {"type": "message", "data": response})
        except Exception as exc:
            logger.warning("Failed to broadcast chat media message", exc_info=exc)

        return response
    except MediaError as exc:
        logger.warning(
            "Media upload failed for user %s receiver %s",
            current_user_id,
            receiver_id,
            exc_info=exc,
        )
        raise BadRequestError(str(exc), code="chat_media_upload_invalid") from exc
    except ChatError as exc:
        logger.warning(
            "Failed to create chat media message for user %s receiver %s",
            current_user_id,
            receiver_id,
            exc_info=exc,
        )
        raise _chat_bad_request(exc, code="chat_media_message_rejected") from exc
    except Exception as exc:
        logger.exception(
            "Unexpected error while creating chat media message for user %s receiver %s origin=%s",
            current_user_id,
            receiver_id,
            request.headers.get("origin"),
        )
        raise InternalServerError(
            "Unexpected error processing media upload. Please check server logs.",
            code="chat_media_upload_failed",
        ) from exc


@router.get("/{peer_id}/messages", response_model=list[MessageResponse])
async def list_messages(
    peer_id: uuid.UUID,
    limit: int = Query(default=50, ge=1, le=100),
    before: datetime | None = Query(default=None),
    cursor: str | None = Query(default=None, description="Optional ISO8601 timestamp cursor for pagination"),
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    """List messages in a conversation.

    Supports legacy `before` datetime query and a minimal `cursor` param (ISO8601 timestamp)
    which will be used as the `before` value if provided.
    """
    current_user_id = current_user.id

    try:
        before = parse_cursor(cursor, before)
    except Exception as exc:
        raise BadRequestError(
            "Invalid cursor format; expected ISO8601 timestamp",
            code="chat_cursor_invalid",
        ) from exc

    try:
        return await get_conversation(session, current_user_id, peer_id, limit, before)
    except ChatError as exc:
        raise _chat_forbidden(exc) from exc


@router.get("/{peer_id}/messages/search", response_model=list[MessageResponse])
async def search_messages(
    peer_id: uuid.UUID,
    q: str = Query(min_length=1, max_length=100),
    limit: int = Query(default=100, ge=1, le=200),
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    current_user_id = current_user.id
    try:
        messages = await get_conversation(session, current_user_id, peer_id, limit)
    except ChatError as exc:
        raise _chat_forbidden(exc) from exc

    return search_records(messages, q, ["content"])


@router.patch("/{peer_id}/messages/{message_id}/seen", response_model=MessageResponse)
async def mark_message_seen_endpoint(
    peer_id: uuid.UUID,
    message_id: uuid.UUID,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    current_user_id = current_user.id
    try:
        return await mark_message_as_seen(session, message_id, current_user_id, peer_id)
    except ChatError as exc:
        raise _chat_forbidden(exc) from exc


@router.delete("/{peer_id}/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_message_endpoint(
    peer_id: uuid.UUID,
    message_id: uuid.UUID,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    current_user_id = current_user.id
    try:
        await delete_message(session, message_id, current_user_id, peer_id)
    except ChatError as exc:
        raise _chat_forbidden(exc) from exc


@router.patch("/{peer_id}/messages/{message_id}", response_model=MessageResponse)
async def update_message_endpoint(
    peer_id: uuid.UUID,
    message_id: uuid.UUID,
    payload: MessageUpdateRequest,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    current_user_id = current_user.id
    try:
        return await update_message(session, message_id, current_user_id, peer_id, payload.content)
    except ChatError as exc:
        raise _chat_forbidden(exc) from exc


@router.post("/{peer_id}/messages/{message_id}/forward", response_model=MessageResponse)
async def forward_message_endpoint(
    peer_id: uuid.UUID,
    message_id: uuid.UUID,
    payload: MessageForwardRequest,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    current_user_id = current_user.id
    try:
        return await forward_message(session, message_id, current_user_id, peer_id, payload.receiver_id)
    except ChatError as exc:
        raise _chat_forbidden(exc) from exc


@router.patch("/{peer_id}/messages/{message_id}/pin", response_model=MessageResponse)
async def toggle_pin_message_endpoint(
    peer_id: uuid.UUID,
    message_id: uuid.UUID,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    current_user_id = current_user.id
    try:
        return await toggle_pin_message(session, message_id, current_user_id, peer_id)
    except ChatError as exc:
        raise _chat_forbidden(exc) from exc


@router.patch("/{peer_id}/messages/{message_id}/reactions", response_model=MessageResponse)
async def toggle_message_reaction_endpoint(
    peer_id: uuid.UUID,
    message_id: uuid.UUID,
    payload: MessageReactionRequest,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    current_user_id = current_user.id
    try:
        return await toggle_message_reaction(session, message_id, current_user_id, peer_id, payload.emoji)
    except ChatError as exc:
        raise _chat_forbidden(exc) from exc


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
        raise _chat_bad_request(exc, code="chat_settings_invalid") from exc
