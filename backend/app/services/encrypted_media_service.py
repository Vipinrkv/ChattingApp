# backend/app/services/encrypted_media_service.py
import base64
import uuid
from pathlib import Path
from typing import Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import SecurityService
from app.core.errors import NotFoundError
from app.models.encrypted_media import EncryptedMedia


class EncryptedMediaService:
    @staticmethod
    async def encrypt_and_store_media(
        session: AsyncSession,
        file_path: Path,
        filename: str,
        media_type: str,
        message_id: uuid.UUID = None,
        post_id: uuid.UUID = None,
    ) -> uuid.UUID:
        """Encrypts media file contents into text, stores it in the database, and returns the media ID."""
        # 1. Read binary data
        bytes_data = file_path.read_bytes()

        # 2. Base64 encode
        base64_str = base64.b64encode(bytes_data).decode("utf-8")

        # 3. Encrypt via AES (Fernet)
        encrypted_data = SecurityService.encrypt_message(base64_str)

        # 4. Save to Database
        encrypted_media = EncryptedMedia(
            message_id=message_id,
            post_id=post_id,
            filename=filename,
            media_type=media_type,
            encrypted_data=encrypted_data,
        )
        session.add(encrypted_media)
        await session.flush()
        return encrypted_media.id

    @staticmethod
    async def retrieve_and_decrypt_media(
        session: AsyncSession,
        media_id: uuid.UUID,
    ) -> Tuple[bytes, str, str]:
        """Retrieves and decrypts database-stored media, returning raw bytes, filename, and media type."""
        result = await session.execute(
            select(EncryptedMedia).where(EncryptedMedia.id == media_id)
        )
        encrypted_media = result.scalar_one_or_none()
        if not encrypted_media:
            raise NotFoundError("Encrypted media not found", code="encrypted_media_not_found")

        # 1. Decrypt data
        decrypted_base64 = SecurityService.decrypt_message(encrypted_media.encrypted_data)

        # 2. Base64 decode to bytes
        bytes_data = base64.b64decode(decrypted_base64.encode("utf-8"))

        return bytes_data, encrypted_media.filename, encrypted_media.media_type
