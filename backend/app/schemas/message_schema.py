# c:\Users\Vipin\OneDrive\Desktop\WebAplications\ChattingApp\backend\app\schemas\message_schema.py
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class MessageCreateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    reply_to_message_id: Optional[uuid.UUID] = None
    media_url: Optional[str] = None
    media_type: Optional[str] = None
    media_name: Optional[str] = None
    media_size: Optional[int] = None


class MessageUpdateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class MessageResponse(BaseModel):
    id: uuid.UUID
    sender_id: uuid.UUID
    receiver_id: uuid.UUID
    content: str
    media_url: Optional[str] = None
    media_type: Optional[str] = None
    media_name: Optional[str] = None
    media_size: Optional[int] = None
    timestamp: datetime
    is_seen: bool
    reply_to_message_id: Optional[uuid.UUID] = None
    reply_preview: Optional[str] = None
    reactions: dict[str, list[str]] = Field(default_factory=dict)
    is_pinned: bool = False
    edited_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ChatSettingsUpdateRequest(BaseModel):
    is_muted: Optional[bool] = None
    is_archived: Optional[bool] = None


class ChatSettingsResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    peer_id: uuid.UUID
    is_muted: bool
    is_archived: bool
    updated_at: datetime

    class Config:
        from_attributes = True


class MessageReactionRequest(BaseModel):
    emoji: str = Field(min_length=1, max_length=16)


class MessageForwardRequest(BaseModel):
    receiver_id: uuid.UUID
