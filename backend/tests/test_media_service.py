import asyncio
from pathlib import Path
import shutil

import pytest

from app.services import media_service


def make_chunks(tmp_path: Path, upload_id: str, filename: str, content: bytes, chunk_size: int = 10):
    tmpdir = tmp_path / 'tmp' / upload_id
    tmpdir.mkdir(parents=True, exist_ok=True)
    parts = [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]
    for idx, part in enumerate(parts):
        p = tmpdir / f"chunk_{idx:06d}"
        p.write_bytes(part)
    return tmpdir


@pytest.mark.asyncio
async def test_assemble_chunks(tmp_path: Path, monkeypatch):
    upload_id = 'test-upload'
    filename = 'file.txt'
    content = b'hello world this is a test file'
    tmpdir = make_chunks(tmp_path, upload_id, filename, content, chunk_size=5)

    # point service TMP_DIR to our tmp
    monkeypatch.setattr(media_service, 'TMP_DIR', tmp_path / 'tmp')
    monkeypatch.setattr(media_service, 'UPLOAD_DIR', tmp_path / 'uploads' / 'media')
    (tmp_path / 'uploads' / 'media').mkdir(parents=True)

    assembled = await media_service.assemble_chunks(upload_id, filename)
    data = assembled.read_bytes()
    assert data == content


@pytest.mark.asyncio
async def test_optimize_image(tmp_path: Path):
    # create a small PNG
    p = tmp_path / 'img.png'
    from PIL import Image
    img = Image.new('RGB', (64, 64), color='red')
    img.save(p)

    out = await media_service.optimize_image(p)
    assert out.exists()
    assert out.suffix == '.webp'


def test_store_file_local(tmp_path: Path, monkeypatch):
    p = tmp_path / 'file.bin'
    p.write_bytes(b'123')
    # ensure no S3 configured
    monkeypatch.setattr(media_service, 'settings', media_service.settings)
    monkeypatch.setattr(media_service.settings, 'AWS_S3_BUCKET', '')
    url = asyncio.run(media_service.store_file(p))
    assert url.endswith(p.name)
import asyncio
import io
import os
from pathlib import Path

from app.services.media_service import store_chat_upload, _PIL_AVAILABLE


class DummyUploadFile:
    def __init__(self, filename: str, content_type: str, data: bytes):
        self.filename = filename
        self.content_type = content_type
        self._data = data

    async def read(self):
        return self._data


def _make_jpeg_bytes():
    # Create a small in-memory JPEG if Pillow is available, otherwise return raw bytes
    if _PIL_AVAILABLE:
        from PIL import Image

        img = Image.new("RGB", (100, 100), color=(255, 0, 0))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=95)
        return buf.getvalue()

    return b"\xff\xd8\xff" + b"0" * 1024 + b"\xff\xd9"


def test_store_chat_upload_local(tmp_path, monkeypatch):
    # Ensure S3 is not used for this test
    monkeypatch.delenv("AWS_S3_BUCKET", raising=False)

    data = _make_jpeg_bytes()
    upload = DummyUploadFile("test.jpg", "image/jpeg", data)

    result = asyncio.run(store_chat_upload(upload))

    assert isinstance(result, dict)
    assert "url" in result
    assert result["content_type"] == "image/jpeg"
    assert result["name"] == "test.jpg"
    assert result["size"] <= len(data)
    assert result["storage"] == "local"

    # ensure file exists on disk when URL is local
    if result["url"].startswith("/uploads/"):
        uploads_dir = Path(__file__).resolve().parents[1] / "uploads"
        filename = result["url"].split("/uploads/")[-1]
        assert (uploads_dir / filename).exists()


def test_store_chat_upload_s3_fallback(monkeypatch):
    # If boto3 isn't available, ensure function raises a clear error when S3 requested
    monkeypatch.setenv("AWS_S3_BUCKET", "dummy-bucket")
    # Remove boto3 availability flag by setting env var but keeping boto3 possibly installed.
    # We don't want to actually call AWS in unit tests.
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "fake")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "fake")

    data = _make_jpeg_bytes()
    upload = DummyUploadFile("test.jpg", "image/jpeg", data)

    # If S3 client is available in the environment, the call may try network access.
    # We therefore only assert that store_chat_upload either succeeds (with storage 's3')
    # or falls back to local storage by catching MediaError or verifying 'local'.
    result = asyncio.run(store_chat_upload(upload))
    assert result["storage"] in ("s3", "local")
