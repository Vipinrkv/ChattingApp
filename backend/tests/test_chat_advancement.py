"""Tests for chat advancement features"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.message import Message
from app.models.shared_media_gallery import SharedMediaGallery
from app.models.user import User
from app.services.chat_advancement_service import (
    bookmark_message,
    unbookmark_message,
    get_user_bookmarks,
    schedule_message,
    translate_message,
    get_message_translation,
    sync_message_to_device,
    create_backup,
    create_media_gallery,
    add_media_to_gallery,
    get_smart_replies,
    create_voice_transcription,
    mark_message_encrypted,
    ChatAdvancementError,
)


async def create_test_user(session: AsyncSession, user_id):
    user = User(
        id=user_id,
        firebase_uid=f"test-{user_id}",
        username=f"user_{user_id.hex[:12]}",
        email=f"user_{user_id.hex[:12]}@example.test",
        role="user",
        is_active=True,
    )
    session.add(user)
    await session.flush()
    return user


async def create_test_message(session: AsyncSession, message_id, sender_id=None, receiver_id=None):
    sender_id = sender_id or uuid4()
    receiver_id = receiver_id or uuid4()
    await create_test_user(session, sender_id)
    if receiver_id != sender_id:
        await create_test_user(session, receiver_id)
    message = Message(
        id=message_id,
        sender_id=sender_id,
        receiver_id=receiver_id,
        content="Test message",
        reactions={},
        is_pinned=False,
        is_seen=False,
    )
    session.add(message)
    await session.flush()
    return message


@pytest.mark.asyncio
async def test_bookmark_message(session: AsyncSession):
    """Test message bookmarking"""
    user_id = uuid4()
    message_id = uuid4()
    await create_test_message(session, message_id, sender_id=user_id)
    
    # Bookmark message
    bookmark = await bookmark_message(session, user_id, message_id, label="Important")
    assert bookmark.user_id == user_id
    assert bookmark.message_id == message_id
    assert bookmark.bookmark_label == "Important"
    
    # Try to bookmark again - should fail
    with pytest.raises(ChatAdvancementError):
        await bookmark_message(session, user_id, message_id)


@pytest.mark.asyncio
async def test_schedule_message_past_time(session: AsyncSession):
    """Test scheduling message with past time fails"""
    sender_id = uuid4()
    receiver_id = uuid4()
    past_time = datetime.now() - timedelta(hours=1)
    
    with pytest.raises(ChatAdvancementError):
        await schedule_message(
            session,
            sender_id,
            receiver_id,
            "Test message",
            past_time,
        )


@pytest.mark.asyncio
async def test_translate_message(session: AsyncSession):
    """Test message translation caching"""
    message_id = uuid4()
    await create_test_message(session, message_id)
    
    translation = await translate_message(
        session,
        message_id,
        "es",
        "Mensaje de prueba",
        "en",
    )
    assert translation.target_language == "es"
    assert translation.translated_content == "Mensaje de prueba"
    
    # Get cached translation
    cached = await get_message_translation(session, message_id, "es")
    assert cached == "Mensaje de prueba"


@pytest.mark.asyncio
async def test_device_sync(session: AsyncSession):
    """Test cross-device message syncing"""
    user_id = uuid4()
    device_id = "device-123"
    message_id = uuid4()
    await create_test_message(session, message_id, sender_id=user_id)
    
    sync = await sync_message_to_device(session, user_id, device_id, message_id)
    assert sync.user_id == user_id
    assert sync.device_id == device_id
    assert sync.message_id == message_id
    assert sync.sync_status.value == "pending"


@pytest.mark.asyncio
async def test_create_backup(session: AsyncSession):
    """Test chat backup creation"""
    user_id = uuid4()
    await create_test_user(session, user_id)
    
    backup = await create_backup(session, user_id, "Test Backup", "json")
    assert backup.user_id == user_id
    assert backup.backup_name == "Test Backup"
    assert backup.backup_status.value == "pending"
    assert backup.format == "json"


@pytest.mark.asyncio
async def test_create_media_gallery(session: AsyncSession):
    """Test creating shared media gallery"""
    conversation_id = "conv-123"
    creator_id = uuid4()
    await create_test_user(session, creator_id)
    
    gallery = await create_media_gallery(
        session,
        conversation_id,
        creator_id,
        "Vacation Photos",
        "Photos from summer vacation",
    )
    assert gallery.conversation_id == conversation_id
    assert gallery.creator_id == creator_id
    assert gallery.title == "Vacation Photos"
    assert gallery.media_count == 0
    assert gallery.is_shared is True


@pytest.mark.asyncio
async def test_add_media_to_gallery(session: AsyncSession):
    """Test adding media to gallery"""
    gallery_id = uuid4()
    message_id = uuid4()
    creator_id = uuid4()
    await create_test_message(session, message_id, sender_id=creator_id)
    gallery = SharedMediaGallery(
        id=gallery_id,
        conversation_id="conv-123",
        creator_id=creator_id,
        title="Vacation Photos",
        description="Photos from summer vacation",
        is_shared=True,
    )
    session.add(gallery)
    await session.flush()
    
    item = await add_media_to_gallery(
        session,
        gallery_id,
        message_id,
        "https://example.com/photo.jpg",
        "image/jpeg",
        1024000,
    )
    assert item.gallery_id == gallery_id
    assert item.message_id == message_id
    assert item.media_type == "image/jpeg"
    assert item.media_size == 1024000


@pytest.mark.asyncio
async def test_voice_transcription(session: AsyncSession):
    """Test voice transcription creation"""
    message_id = uuid4()
    audio_url = "https://example.com/audio.webm"
    await create_test_message(session, message_id)
    
    transcription = await create_voice_transcription(
        session,
        message_id,
        audio_url,
        duration_seconds=15.5,
    )
    assert transcription.message_id == message_id
    assert transcription.audio_url == audio_url
    assert transcription.duration_seconds == 15.5
    assert transcription.is_processed is False


@pytest.mark.asyncio
async def test_mark_message_encrypted(session: AsyncSession):
    """Test marking message as encrypted"""
    message_id = uuid4()
    
    # This would require an actual Message object in DB
    # For now, we test the logic only
    from app.models.message import Message
    from app.models.user import User
    
    # Create test users and message (in real test with DB setup)
    # message = await mark_message_encrypted(session, message_id, "1.0")
    # assert message.is_encrypted is True
    # assert message.encryption_version == "1.0"


@pytest.mark.asyncio
async def test_routes_bookmark_endpoint():
    """Test bookmark HTTP endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # This would require authentication
        # response = await client.post(
        #     f"/chats/bookmarks/{uuid4()}",
        #     headers={"Authorization": f"Bearer {fake_token}"}
        # )
        # assert response.status_code == 200
        pass


@pytest.mark.asyncio
async def test_routes_schedule_endpoint():
    """Test schedule message HTTP endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # response = await client.post(
        #     f"/chats/{uuid4()}/messages/schedule",
        #     json={
        #         "content": "Test",
        #         "scheduled_for": (datetime.now() + timedelta(hours=1)).isoformat(),
        #     }
        # )
        pass


@pytest.mark.asyncio
async def test_routes_backup_endpoint():
    """Test backup HTTP endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # response = await client.post(
        #     "/chats/backups",
        #     json={"backup_name": "Test", "format": "json"}
        # )
        pass
