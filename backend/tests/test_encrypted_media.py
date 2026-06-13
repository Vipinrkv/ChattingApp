import pytest
from httpx import AsyncClient
from pathlib import Path
import uuid
from unittest.mock import patch

from app.main import app
from app.services import media_service
from app.services.encrypted_media_service import EncryptedMediaService
from app.models.user import User
from app.core.firebase import FirebaseService
from app.core.auth import get_current_user as get_current_user_dep


@pytest.mark.asyncio
async def test_encrypted_media_service_direct(session, tmp_path):
    # 1. Create a dummy file
    dummy_file = tmp_path / "test_media.txt"
    dummy_file.write_bytes(b"Secret media content 123!")

    # 2. Encrypt and store
    media_id = await EncryptedMediaService.encrypt_and_store_media(
        session=session,
        file_path=dummy_file,
        filename="test_media.txt",
        media_type="text/plain"
    )
    assert media_id is not None
    assert isinstance(media_id, uuid.UUID)

    # 3. Retrieve and decrypt
    decrypted_bytes, filename, media_type = await EncryptedMediaService.retrieve_and_decrypt_media(
        session=session,
        media_id=media_id
    )
    assert decrypted_bytes == b"Secret media content 123!"
    assert filename == "test_media.txt"
    assert media_type == "text/plain"


@pytest.mark.asyncio
async def test_encrypted_media_route_flow(session, tmp_path, monkeypatch):
    # Monkeypatch media directories
    monkeypatch.setattr(media_service, 'TMP_DIR', tmp_path / 'tmp')
    monkeypatch.setattr(media_service, 'UPLOAD_DIR', tmp_path / 'uploads' / 'media')
    monkeypatch.setattr(media_service, 'schedule_post_processing', _async_noop)
    monkeypatch.setattr(media_service, 'ai_tag_media', _async_empty_list)
    (tmp_path / 'uploads' / 'media').mkdir(parents=True, exist_ok=True)

    # Create dummy user in DB
    user = User(
        firebase_uid="test-firebase-uid",
        username="testuser_enc",
        email="testenc@example.com",
        role="user"
    )
    session.add(user)
    await session.commit()

    # Override get_current_user dependency for upload route
    async def fake_user_dep():
        return user

    app.dependency_overrides[get_current_user_dep] = fake_user_dep
    headers = {'Authorization': 'Bearer valid-test-token'}

    try:
        async with AsyncClient(app=app, base_url='http://test') as client:
            # 1. Initiate upload
            res = await client.post('/api/v1/media/upload/initiate', data={'filename': 'secret.txt'}, headers=headers)
            assert res.status_code == 200
            upload_id = res.json().get('upload_id')
            assert upload_id

            # 2. Upload chunk
            files = {'file': ('chunk.bin', b'encrypted payload hello')}
            data = {'chunk_index': '0'}
            res = await client.post(f'/api/v1/media/upload/{upload_id}/chunk', data=data, files=files, headers=headers)
            assert res.status_code == 200

            # 3. Complete upload with encrypt=True
            res = await client.post(
                f'/api/v1/media/upload/{upload_id}/complete',
                data={'filename': 'secret.txt', 'encrypt': True},
                headers=headers
            )
            assert res.status_code == 200
            payload = res.json()
            assert 'url' in payload
            url = payload['url']
            assert "/api/v1/media/encrypted/" in url
            
            # Extract media_id from url
            media_id_str = url.split("/")[-1]
            media_id = uuid.UUID(media_id_str)

            # 4. GET encrypted media with valid token
            # Mock Firebase verification
            with patch.object(FirebaseService, 'verify_token', return_value={"uid": "test-firebase-uid"}):
                res = await client.get(f'/api/v1/media/encrypted/{media_id}?token=valid-test-token')
                assert res.status_code == 200
                assert res.content == b'encrypted payload hello'

            # 5. GET encrypted media with missing token
            res = await client.get(f'/api/v1/media/encrypted/{media_id}')
            assert res.status_code == 401
            assert "Missing authentication token" in res.json()["error"]["message"]

            # 6. GET encrypted media with invalid token
            with patch.object(FirebaseService, 'verify_token', return_value=None):
                res = await client.get(f'/api/v1/media/encrypted/{media_id}?token=invalid-test-token')
                assert res.status_code == 401
                assert "Invalid or expired token" in res.json()["error"]["message"]

            # 7. GET encrypted media for non-existent ID
            fake_media_id = uuid.uuid4()
            with patch.object(FirebaseService, 'verify_token', return_value={"uid": "test-firebase-uid"}):
                res = await client.get(f'/api/v1/media/encrypted/{fake_media_id}?token=valid-test-token')
                assert res.status_code == 404
                assert "Encrypted media not found" in res.json()["error"]["message"]

    finally:
        app.dependency_overrides.pop(get_current_user_dep, None)


async def _async_noop(*args, **kwargs):
    return None


async def _async_empty_list(*args, **kwargs):
    return []
