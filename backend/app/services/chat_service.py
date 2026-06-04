# c:\Users\Vipin\OneDrive\Desktop\WebAplications\ChattingApp\backend\app\services\chat_service.py
import uuid
from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import ensure_not_self
from app.core.query import apply_limit, apply_order_by
from app.core.transaction import run_transaction
from app.core.security import decrypt_value, encrypt_value
from app.models.chat_settings import ChatSettings
from app.models.message import Message
from app.services.block_service import are_blocked, user_exists
from app.services.notification_service import NotificationService
from app.services.moderation_service import ModerationError, ModerationService


class ChatError(Exception):
    pass


def serialize_message(message: Message) -> dict:
    return {
        "id": str(message.id),
        "sender_id": str(message.sender_id),
        "receiver_id": str(message.receiver_id),
        "content": decrypt_value(message.content),
        "media_url": message.media_url,
        "media_type": message.media_type,
        "media_name": message.media_name,
        "media_size": message.media_size,
        "timestamp": message.timestamp,
        "is_seen": message.is_seen,
        "reply_to_message_id": str(message.reply_to_message_id) if message.reply_to_message_id else None,
        "reply_preview": None,
        "reactions": message.reactions or {},
        "is_pinned": message.is_pinned,
        "edited_at": message.edited_at,
    }


async def _get_message_in_conversation(
    session: AsyncSession,
    message_id: uuid.UUID,
    user_id: uuid.UUID,
    peer_id: uuid.UUID,
) -> Message:
    result = await session.execute(
        select(Message).where(Message.id == message_id)
    )
    message = result.scalar_one_or_none()

    if not message:
        raise ChatError("Message not found")

    is_valid_context = (
        (message.sender_id == user_id and message.receiver_id == peer_id)
        or (message.sender_id == peer_id and message.receiver_id == user_id)
    )
    if not is_valid_context:
        raise ChatError("Invalid message context")

    return message


async def send_message(
    session: AsyncSession,
    sender_id: uuid.UUID,
    receiver_id: uuid.UUID,
    content: str,
    reply_to_message_id: uuid.UUID | None = None,
) -> Message:
    try:
        ensure_not_self(sender_id, receiver_id, "Cannot send a message to yourself")
    except Exception as exc:
        raise ChatError(str(exc)) from exc

    await ModerationService.validate_user_can_send(session, str(sender_id))
    await ModerationService.validate_text_content(content)
    await ModerationService.enforce_message_rate_limit(session, str(sender_id))

    ai_result = await ModerationService.validate_content_with_ai(
        session,
        content_id=str(uuid.uuid4()),
        content_type="message",
        content_text=content,
    )
    if ai_result.get("should_auto_moderate"):
        await ModerationService.apply_ai_auto_moderation(
            session,
            str(sender_id),
            ai_result.get("content_id"),
            ai_analysis=ai_result,
        )
        raise ChatError("Message blocked by AI moderation policy")

    if not await user_exists(session, receiver_id):
        raise ChatError("Receiver not found")
    if await are_blocked(session, sender_id, receiver_id):
        raise ChatError("Message is not allowed")

    if reply_to_message_id:
        await _get_message_in_conversation(session, reply_to_message_id, sender_id, receiver_id)

    message = Message(
        sender_id=sender_id,
        receiver_id=receiver_id,
        content=encrypt_value(content),
        reply_to_message_id=reply_to_message_id,
    )

    async def persist_message() -> Message:
        session.add(message)
        await session.refresh(message)
        return message

    message = await run_transaction(session, persist_message)

    # Create a notification for the receiver (best-effort)
    try:
        # Use decrypted content for notification text where possible
        notif_text = decrypt_value(message.content)
        await NotificationService.create_notification(
            session,
            user_id=str(receiver_id),
            type="message",
            text=notif_text,
            actor_id=str(sender_id),
            data={"message_id": str(message.id)},
        )
    except Exception:
        pass

    return message


async def send_media_message(
    session: AsyncSession,
    sender_id: uuid.UUID,
    receiver_id: uuid.UUID,
    content: str,
    media_url: str,
    media_type: str,
    media_name: str,
    media_size: int,
) -> Message:
    try:
        ensure_not_self(sender_id, receiver_id, "Cannot send a message to yourself")
    except Exception as exc:
        raise ChatError(str(exc)) from exc

    await ModerationService.validate_user_can_send(session, str(sender_id))
    await ModerationService.validate_text_content(content)
    await ModerationService.enforce_message_rate_limit(session, str(sender_id))

    ai_result = await ModerationService.validate_content_with_ai(
        session,
        content_id=str(uuid.uuid4()),
        content_type="message",
        content_text=content,
    )
    if ai_result.get("should_auto_moderate"):
        await ModerationService.apply_ai_auto_moderation(
            session,
            str(sender_id),
            ai_result.get("content_id"),
            ai_analysis=ai_result,
        )
        raise ChatError("Media message blocked by AI moderation policy")

    if not await user_exists(session, receiver_id):
        raise ChatError("Receiver not found")
    if await are_blocked(session, sender_id, receiver_id):
        raise ChatError("Message is not allowed")

    message = Message(
        sender_id=sender_id,
        receiver_id=receiver_id,
        content=encrypt_value(content or media_name),
        media_url=media_url,
        media_type=media_type,
        media_name=media_name,
        media_size=media_size,
    )

    session.add(message)
    await session.flush()
    await session.refresh(message)

    # Create a notification for the receiver (best-effort)
    try:
        notif_text = decrypt_value(message.content) if message.content else (message.media_name or "")
        await NotificationService.create_notification(
            session,
            user_id=str(receiver_id),
            type="message",
            text=notif_text,
            actor_id=str(sender_id),
            data={"message_id": str(message.id), "media_url": message.media_url},
        )
    except Exception:
        pass

    return message


async def get_conversation(
    session: AsyncSession,
    user_id: uuid.UUID,
    peer_id: uuid.UUID,
    limit: int = 50,
    before: datetime | None = None,
) -> list[dict]:
    if await are_blocked(session, user_id, peer_id):
        raise ChatError("Conversation is not available")

    query = (
        select(Message)
        .where(
            or_(
                (Message.sender_id == user_id) & (Message.receiver_id == peer_id),
                (Message.sender_id == peer_id) & (Message.receiver_id == user_id),
            )
        )
    )

    if before:
        query = query.where(Message.timestamp < before)

    query = apply_order_by(query, Message.timestamp, 'desc')
    query = apply_limit(query, limit)
    result = await session.execute(query)
    messages = list(result.scalars().all())
    messages.reverse()
    messages = await ModerationService.filter_shadowbanned_messages(
        session,
        messages,
        str(user_id),
        viewer_is_admin=False,
    )
    return [serialize_message(message) for message in messages]


async def get_conversation_since(
    session: AsyncSession,
    user_id: uuid.UUID,
    peer_id: uuid.UUID,
    since: datetime | None = None,
    limit: int = 100,
) -> list[dict]:
    if await are_blocked(session, user_id, peer_id):
        raise ChatError("Conversation is not available")

    query = (
        select(Message)
        .where(
            or_(
                (Message.sender_id == user_id) & (Message.receiver_id == peer_id),
                (Message.sender_id == peer_id) & (Message.receiver_id == user_id),
            )
        )
    )

    if since:
        query = query.where(Message.timestamp > since)

    query = apply_order_by(query, Message.timestamp, 'asc')
    query = apply_limit(query, limit)
    result = await session.execute(query)
    messages = list(result.scalars().all())
    messages = await ModerationService.filter_shadowbanned_messages(
        session,
        messages,
        str(user_id),
        viewer_is_admin=False,
    )
    return [serialize_message(message) for message in messages]


async def update_chat_settings(
    session: AsyncSession,
    user_id: uuid.UUID,
    peer_id: uuid.UUID,
    is_muted: bool | None,
    is_archived: bool | None,
) -> ChatSettings:
    try:
        ensure_not_self(user_id, peer_id, "Cannot update settings for yourself")
    except Exception as exc:
        raise ChatError(str(exc)) from exc

    if not await user_exists(session, peer_id):
        raise ChatError("Peer not found")

    result = await session.execute(
        select(ChatSettings).where(
            ChatSettings.user_id == user_id,
            ChatSettings.peer_id == peer_id,
        )
    )
    settings = result.scalar_one_or_none()
    if not settings:
        settings = ChatSettings(user_id=user_id, peer_id=peer_id)
        session.add(settings)

    if is_muted is not None:
        settings.is_muted = is_muted
    if is_archived is not None:
        settings.is_archived = is_archived

    async def persist_settings() -> ChatSettings:
        await session.refresh(settings)
        return settings

    return await run_transaction(session, persist_settings)


async def mark_message_as_seen(
    session: AsyncSession,
    message_id: uuid.UUID,
    user_id: uuid.UUID,
    peer_id: uuid.UUID,
) -> dict:
    """Mark a message as seen by the receiving user"""
    message = await _get_message_in_conversation(session, message_id, user_id, peer_id)

    if message.receiver_id != user_id:
        raise ChatError("You cannot mark this message as seen")

    message.is_seen = True

    async def persist_seen() -> dict:
        await session.refresh(message)
        return serialize_message(message)

    return await run_transaction(session, persist_seen)


async def delete_message(
    session: AsyncSession,
    message_id: uuid.UUID,
    user_id: uuid.UUID,
    peer_id: uuid.UUID,
) -> None:
    message = await _get_message_in_conversation(session, message_id, user_id, peer_id)

    if message.sender_id != user_id:
        raise ChatError("You can only delete messages you sent")

    async def persist_deletion() -> None:
        await session.delete(message)

    await run_transaction(session, persist_deletion)


async def update_message(
    session: AsyncSession,
    message_id: uuid.UUID,
    user_id: uuid.UUID,
    peer_id: uuid.UUID,
    content: str,
) -> dict:
    message = await _get_message_in_conversation(session, message_id, user_id, peer_id)

    if message.sender_id != user_id:
        raise ChatError("You can only edit messages you sent")

    message.content = encrypt_value(content)
    message.edited_at = datetime.now(timezone.utc)

    async def persist_message_update() -> dict:
        await session.refresh(message)
        return serialize_message(message)

    return await run_transaction(session, persist_message_update)


async def forward_message(
    session: AsyncSession,
    message_id: uuid.UUID,
    user_id: uuid.UUID,
    peer_id: uuid.UUID,
    receiver_id: uuid.UUID,
) -> dict:
    source = await _get_message_in_conversation(session, message_id, user_id, peer_id)
    content = decrypt_value(source.content)
    forwarded = await send_message(session, user_id, receiver_id, content)
    return serialize_message(forwarded)


async def toggle_pin_message(
    session: AsyncSession,
    message_id: uuid.UUID,
    user_id: uuid.UUID,
    peer_id: uuid.UUID,
) -> dict:
    message = await _get_message_in_conversation(session, message_id, user_id, peer_id)
    message.is_pinned = not message.is_pinned

    async def persist_pin_toggle() -> dict:
        await session.refresh(message)
        return serialize_message(message)

    return await run_transaction(session, persist_pin_toggle)


async def toggle_message_reaction(
    session: AsyncSession,
    message_id: uuid.UUID,
    user_id: uuid.UUID,
    peer_id: uuid.UUID,
    emoji: str,
) -> dict:
    message = await _get_message_in_conversation(session, message_id, user_id, peer_id)
    reactions = dict(message.reactions or {})
    user_key = str(user_id)
    users = list(reactions.get(emoji, []))

    if user_key in users:
        users.remove(user_key)
    else:
        users.append(user_key)

    if users:
        reactions[emoji] = users
    else:
        reactions.pop(emoji, None)

    message.reactions = reactions

    async def persist_reactions() -> dict:
        await session.refresh(message)
        return serialize_message(message)

    return await run_transaction(session, persist_reactions)
