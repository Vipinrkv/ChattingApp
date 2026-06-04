"""Routes for chat system advancement features

Endpoints for:
1. Message bookmarking
2. Scheduled messages
3. Message translation
4. Cross-device sync
5. Chat backup/export
6. Shared media gallery
7. AI smart replies
8. Voice transcription
9. End-to-end encryption
"""
import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user as get_current_user_dep
from app.core.errors import BadRequestError, InternalServerError, NotFoundError
from app.database.connection import get_db_session
from app.models.user import User
from app.schemas.chat_advancement_schema import (
    BackupCreateRequest,
    GalleryCreateRequest,
    GalleryMediaCreateRequest,
    ScheduleMessageRequest,
    TranslateMessageRequest,
    VoiceMessageRequest,
    EncryptionMarkRequest,
)
from app.services.chat_advancement_service import (
    ChatAdvancementError,
    bookmark_message,
    unbookmark_message,
    get_user_bookmarks,
    schedule_message,
    cancel_scheduled_message,
    translate_message,
    get_message_translation,
    sync_message_to_device,
    mark_sync_complete,
    get_pending_syncs,
    create_backup,
    get_user_backups,
    create_media_gallery,
    add_media_to_gallery,
    get_gallery_media,
    get_smart_replies,
    mark_reply_used,
    create_voice_transcription,
    mark_message_encrypted,
    get_encryption_metadata,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/chats",
    tags=["chat-advancement"],
    dependencies=[Depends(get_current_user_dep)],
)


def _chat_advancement_bad_request(exc: Exception) -> BadRequestError:
    return BadRequestError(str(exc), code="chat_advancement_invalid")


# ============================================================================
# 1. MESSAGE BOOKMARKS ENDPOINTS
# ============================================================================

@router.post("/bookmarks/{message_id}")
async def add_bookmark(
    message_id: uuid.UUID,
    label: str | None = Query(None),
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    """Bookmark a message"""
    try:
        bookmark = await bookmark_message(session, current_user.id, message_id, label)
        await session.commit()
        return {
            "bookmark_id": str(bookmark.id),
            "message_id": str(message_id),
            "label": label,
            "created_at": bookmark.created_at.isoformat(),
        }
    except ChatAdvancementError as e:
        raise _chat_advancement_bad_request(e) from e


@router.delete("/bookmarks/{message_id}")
async def remove_bookmark(
    message_id: uuid.UUID,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    """Remove a bookmark from a message"""
    try:
        await unbookmark_message(session, current_user.id, message_id)
        await session.commit()
        return {"success": True}
    except ChatAdvancementError as e:
        raise _chat_advancement_bad_request(e) from e


@router.get("/bookmarks")
async def list_bookmarks(
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    """Get all bookmarks for current user"""
    bookmarks = await get_user_bookmarks(session, current_user.id, limit, offset)
    return {"bookmarks": bookmarks, "total": len(bookmarks)}


# ============================================================================
# 2. SCHEDULED MESSAGES ENDPOINTS
# ============================================================================

@router.post("/{receiver_id}/messages/schedule")
async def schedule_new_message(
    receiver_id: uuid.UUID,
    payload: ScheduleMessageRequest = Body(...),
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    """Schedule a message to be sent at a future time"""
    try:
        scheduled = await schedule_message(
            session,
            current_user.id,
            receiver_id,
            payload.content,
            payload.scheduled_for,
            str(payload.media_url) if payload.media_url else None,
            payload.media_type,
        )
        await session.commit()
        return {
            "scheduled_id": str(scheduled.id),
            "receiver_id": str(receiver_id),
            "scheduled_for": payload.scheduled_for.isoformat(),
            "status": "scheduled",
        }
    except ChatAdvancementError as e:
        raise _chat_advancement_bad_request(e) from e


@router.delete("/messages/scheduled/{scheduled_id}")
async def cancel_scheduled(
    scheduled_id: uuid.UUID,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    """Cancel a scheduled message"""
    try:
        await cancel_scheduled_message(session, scheduled_id, current_user.id)
        await session.commit()
        return {"success": True}
    except ChatAdvancementError as e:
        raise _chat_advancement_bad_request(e) from e


# ============================================================================
# 3. MESSAGE TRANSLATION ENDPOINTS
# ============================================================================

@router.post("/messages/{message_id}/translate")
async def translate_msg(
    message_id: uuid.UUID,
    payload: TranslateMessageRequest = Body(...),
    session: AsyncSession = Depends(get_db_session),
):
    """Translate and cache a message translation"""
    try:
        translation = await translate_message(
            session,
            message_id,
            payload.target_language,
            payload.translated_text,
            payload.source_language,
        )
        await session.commit()
        return {
            "message_id": str(message_id),
            "target_language": payload.target_language,
            "translated_content": translation.translated_content,
        }
    except ChatAdvancementError as e:
        raise _chat_advancement_bad_request(e) from e


@router.get("/messages/{message_id}/translations/{target_language}")
async def get_translation(
    message_id: uuid.UUID,
    target_language: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Get cached translation for a message"""
    translation = await get_message_translation(session, message_id, target_language)
    if not translation:
        raise NotFoundError("Translation not found", code="chat_translation_not_found")
    return {"message_id": str(message_id), "translation": translation}


# ============================================================================
# 4. DEVICE SYNC ENDPOINTS
# ============================================================================

@router.post("/sync/messages/{message_id}")
async def sync_to_device(
    message_id: uuid.UUID,
    device_id: str,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    """Sync a message to a specific device"""
    try:
        sync = await sync_message_to_device(session, current_user.id, device_id, message_id)
        await session.commit()
        return {
            "sync_id": str(sync.id),
            "message_id": str(message_id),
            "device_id": device_id,
            "status": "pending",
        }
    except ChatAdvancementError as e:
        raise _chat_advancement_bad_request(e) from e


@router.get("/sync/pending")
async def get_pending_device_syncs(
    device_id: str,
    limit: int = Query(100, le=500),
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    """Get pending syncs for current user's device"""
    syncs = await get_pending_syncs(session, current_user.id, device_id, limit)
    return {
        "pending_syncs": [
            {"sync_id": str(s.id), "message_id": str(s.message_id)} for s in syncs
        ],
        "total": len(syncs),
    }


@router.post("/sync/{sync_id}/complete")
async def mark_synced(
    sync_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
):
    """Mark a sync as complete"""
    try:
        await mark_sync_complete(session, sync_id)
        await session.commit()
        return {"success": True}
    except ChatAdvancementError as e:
        raise _chat_advancement_bad_request(e) from e


# ============================================================================
# 5. CHAT BACKUP/EXPORT ENDPOINTS
# ============================================================================

@router.post("/backups")
async def initiate_backup(
    payload: BackupCreateRequest = Body(...),
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    """Initiate a chat backup"""
    try:
        backup = await create_backup(session, current_user.id, payload.backup_name, payload.format)
        await session.commit()
        return {
            "backup_id": str(backup.id),
            "backup_name": payload.backup_name,
            "status": "pending",
            "created_at": backup.created_at.isoformat(),
        }
    except ChatAdvancementError as e:
        logger.warning("backup_create_failed", extra={"user_id": str(current_user.id), "reason": str(e)})
        raise BadRequestError(str(e), code="chat_backup_invalid") from e
    except SQLAlchemyError as e:
        logger.exception("backup_create_db_error", extra={"user_id": str(current_user.id), "exception_type": type(e).__name__, "exception_message": str(e)})
        raise InternalServerError(
            "Backup storage is unavailable. Check database migrations.",
            code="chat_backup_storage_unavailable",
        ) from e


@router.get("/backups")
async def list_user_backups(
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    """Get all backups for current user"""
    try:
        backups = await get_user_backups(session, current_user.id, limit, offset)
        return {
            "backups": [
                {
                    "backup_id": str(b.id),
                    "backup_name": b.backup_name,
                    "status": b.backup_status.value,
                    "message_count": b.message_count,
                    "file_size_bytes": b.file_size_bytes,
                    "created_at": b.created_at.isoformat(),
                    "download_url": b.storage_url,
                }
                for b in backups
            ],
            "total": len(backups),
        }
    except SQLAlchemyError as e:
        logger.exception("backup_list_db_error", extra={"user_id": str(current_user.id), "exception_type": type(e).__name__, "exception_message": str(e)})
        raise InternalServerError(
            "Backup storage is unavailable. Check database migrations.",
            code="chat_backup_storage_unavailable",
        ) from e


# ============================================================================
# 6. SHARED MEDIA GALLERY ENDPOINTS
# ============================================================================

@router.post("/{receiver_id}/galleries")
async def create_gallery(
    receiver_id: uuid.UUID,
    payload: GalleryCreateRequest = Body(...),
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    """Create a shared media gallery"""
    conversation_id = f"{min(str(current_user.id), str(receiver_id))}-{max(str(current_user.id), str(receiver_id))}"
    try:
        gallery = await create_media_gallery(
            session,
            conversation_id,
            current_user.id,
            payload.title,
            payload.description,
        )
        await session.commit()
        return {
            "gallery_id": str(gallery.id),
            "title": payload.title,
            "media_count": 0,
            "created_at": gallery.created_at.isoformat(),
        }
    except ChatAdvancementError as e:
        raise _chat_advancement_bad_request(e) from e


@router.post("/galleries/{gallery_id}/media")
async def add_media(
    gallery_id: uuid.UUID,
    payload: GalleryMediaCreateRequest = Body(...),
    session: AsyncSession = Depends(get_db_session),
):
    """Add media to a gallery"""
    try:
        item = await add_media_to_gallery(
            session,
            gallery_id,
            payload.message_id,
            str(payload.media_url),
            payload.media_type,
            payload.media_size,
        )
        await session.commit()
        return {
            "item_id": str(item.id),
            "media_url": str(payload.media_url),
            "media_type": payload.media_type,
            "added_at": item.added_at.isoformat(),
        }
    except ChatAdvancementError as e:
        raise _chat_advancement_bad_request(e) from e


@router.get("/galleries/{gallery_id}/media")
async def list_gallery_media(
    gallery_id: uuid.UUID,
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db_session),
):
    """Get all media in a gallery"""
    media_items = await get_gallery_media(session, gallery_id, limit, offset)
    return {
        "media": [
            {
                "item_id": str(item.id),
                "media_url": item.media_url,
                "media_type": item.media_type,
                "media_size": item.media_size,
                "added_at": item.added_at.isoformat(),
            }
            for item in media_items
        ],
        "total": len(media_items),
    }


# ============================================================================
# 7. AI SMART REPLIES ENDPOINTS
# ============================================================================

@router.get("/messages/{message_id}/smart-replies")
async def get_message_smart_replies(
    message_id: uuid.UUID,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    """Get AI smart reply suggestions for a message"""
    replies = await get_smart_replies(session, message_id, current_user.id, limit=3)
    return {
        "message_id": str(message_id),
        "suggestions": [
            {
                "reply_id": str(r.id),
                "text": r.reply_text,
                "confidence": r.confidence_score,
            }
            for r in replies
        ],
    }


@router.post("/smart-replies/{reply_id}/use")
async def use_smart_reply(
    reply_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
):
    """Mark a smart reply as used"""
    try:
        await mark_reply_used(session, reply_id)
        await session.commit()
        return {"success": True}
    except ChatAdvancementError as e:
        raise _chat_advancement_bad_request(e) from e


# ============================================================================
# 8. VOICE TRANSCRIPTION ENDPOINTS
# ============================================================================

@router.post("/messages/{message_id}/voice")
async def upload_voice_message(
    message_id: uuid.UUID,
    payload: VoiceMessageRequest = Body(...),
    session: AsyncSession = Depends(get_db_session),
):
    """Create a voice transcription record"""
    try:
        transcription = await create_voice_transcription(session, message_id, str(payload.audio_url), payload.duration_seconds)
        await session.commit()
        return {
            "transcription_id": str(transcription.id),
            "message_id": str(message_id),
            "audio_url": str(payload.audio_url),
            "status": "pending",
        }
    except ChatAdvancementError as e:
        raise _chat_advancement_bad_request(e) from e


@router.get("/messages/{message_id}/transcription")
async def get_message_transcription(
    message_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
):
    """Get transcription for a voice message"""
    try:
        from sqlalchemy import select
        from app.models.voice_transcription import VoiceTranscription
        stmt = select(VoiceTranscription).where(VoiceTranscription.message_id == message_id)
        transcription = await session.scalar(stmt)
        if not transcription:
            raise NotFoundError("Transcription not found", code="chat_transcription_not_found")
        
        return {
            "transcription_id": str(transcription.id),
            "transcribed_text": transcription.transcribed_text,
            "source_language": transcription.source_language,
            "confidence_score": transcription.confidence_score,
            "is_processed": transcription.is_processed,
        }
    except NotFoundError:
        raise
    except Exception as e:
        raise BadRequestError(str(e), code="chat_transcription_invalid") from e


# ============================================================================
# 9. END-TO-END ENCRYPTION ENDPOINTS
# ============================================================================

@router.patch("/messages/{message_id}/encryption")
async def mark_message_encryption(
    message_id: uuid.UUID,
    payload: EncryptionMarkRequest = Body(...),
    session: AsyncSession = Depends(get_db_session),
):
    """Mark a message as encrypted"""
    try:
        message = await mark_message_encrypted(session, message_id, payload.encryption_version)
        await session.commit()
        return {
            "message_id": str(message_id),
            "is_encrypted": message.is_encrypted,
            "encryption_version": message.encryption_version,
        }
    except ChatAdvancementError as e:
        raise _chat_advancement_bad_request(e) from e


@router.get("/messages/{message_id}/encryption")
async def get_message_encryption_info(
    message_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
):
    """Get encryption metadata for a message"""
    metadata = await get_encryption_metadata(session, message_id)
    if not metadata:
        raise NotFoundError("Message not found", code="chat_message_not_found")
    return {"message_id": str(message_id), "encryption": metadata}
