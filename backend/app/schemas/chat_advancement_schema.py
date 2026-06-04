import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class ScheduleMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    scheduled_for: datetime
    media_url: Optional[HttpUrl] = None
    media_type: Optional[str] = None


class TranslateMessageRequest(BaseModel):
    target_language: str = Field(min_length=2, max_length=16)
    translated_text: str = Field(min_length=1, max_length=4000)
    source_language: Optional[str] = Field(default='auto')


class GalleryCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None


class GalleryMediaCreateRequest(BaseModel):
    message_id: uuid.UUID
    media_url: HttpUrl
    media_type: str
    media_size: Optional[int] = None


class BackupCreateRequest(BaseModel):
    backup_name: str = Field(min_length=1, max_length=255)
    format: str = Field(default='json')


class VoiceMessageRequest(BaseModel):
    audio_url: HttpUrl
    duration_seconds: Optional[float] = None


class EncryptionMarkRequest(BaseModel):
    encryption_version: Optional[str] = Field(default='1.0')
