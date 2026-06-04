import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class SuggestedUser(BaseModel):
    id: uuid.UUID
    username: str
    score: float
    reason: str
    is_verified: bool = False

    class Config:
        from_attributes = True


class MutualFriend(BaseModel):
    id: uuid.UUID
    username: str

    class Config:
        from_attributes = True


class CloseFriendCreate(BaseModel):
    friend_id: uuid.UUID


class PollCreate(BaseModel):
    question: str = Field(min_length=1, max_length=240)
    options: list[str] = Field(min_length=2, max_length=6)
    expires_at: datetime | None = None


class PollVote(BaseModel):
    option: str = Field(min_length=1, max_length=120)


class PollResponse(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    question: str
    options: list[str]
    votes: dict[str, int]
    expires_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class StoryCreate(BaseModel):
    media_url: str = Field(min_length=1)
    caption: str | None = Field(default=None, max_length=240)
    audience: str = "friends"


class StoryResponse(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    media_url: str
    caption: str | None
    audience: str
    expires_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class ShortVideoCreate(BaseModel):
    video_url: str = Field(min_length=1)
    thumbnail_url: str | None = None
    caption: str | None = Field(default=None, max_length=240)
    duration_seconds: int | None = Field(default=None, ge=0)


class ShortVideoResponse(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    video_url: str
    thumbnail_url: str | None
    caption: str | None
    duration_seconds: int | None
    created_at: datetime

    class Config:
        from_attributes = True


class VerificationRequestCreate(BaseModel):
    reason: str | None = None
    evidence: dict[str, object] = Field(default_factory=dict)
