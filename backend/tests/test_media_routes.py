import asyncio
import os
from pathlib import Path

import pytest
from httpx import AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_media_upload_flow(tmp_path: Path, monkeypatch):
    # Ensure TMP_DIR points to tmp_path
    from app.services import media_service
    monkeypatch.setattr(media_service, 'TMP_DIR', tmp_path / 'tmp')
    monkeypatch.setattr(media_service, 'UPLOAD_DIR', tmp_path / 'uploads' / 'media')
    monkeypatch.setattr(media_service, 'schedule_post_processing', _async_noop)
    monkeypatch.setattr(media_service, 'ai_tag_media', _async_empty_list)
    (tmp_path / 'uploads' / 'media').mkdir(parents=True, exist_ok=True)

    from app.core.auth import get_current_user as get_current_user_dep

    async def fake_user_dep():
        class U:
            pass

        u = U()
        u.id = '00000000-0000-0000-0000-000000000000'
        return u

    app.dependency_overrides[get_current_user_dep] = fake_user_dep
    headers = {'Authorization': 'Bearer test-token'}

    try:
        async with AsyncClient(app=app, base_url='http://test') as client:
            # initiate
            res = await client.post('/api/v1/media/upload/initiate', data={'filename': 'test.txt'}, headers=headers)
            assert res.status_code == 200
            upload_id = res.json().get('upload_id')
            assert upload_id

            # upload chunk
            files = {'file': ('chunk.bin', b'hello world')}
            data = {'chunk_index': '0'}
            res = await client.post(f'/api/v1/media/upload/{upload_id}/chunk', data=data, files=files, headers=headers)
            assert res.status_code == 200

            # complete
            res = await client.post(f'/api/v1/media/upload/{upload_id}/complete', data={'filename': 'test.txt'}, headers=headers)
            assert res.status_code == 200
            payload = res.json()
            assert 'url' in payload
    finally:
        app.dependency_overrides.pop(get_current_user_dep, None)


async def _async_noop(*args, **kwargs):
    return None


async def _async_empty_list(*args, **kwargs):
    return []
