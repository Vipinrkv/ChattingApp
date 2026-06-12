# c:\Users\Vipin\OneDrive\Desktop\WebAplications\ChattingApp\backend\app\schemas\friend_schema.py
import uuid
from datetime import datetime

from pydantic import BaseModel, validator


class FriendRequestResponse(BaseModel):
    id: uuid.UUID
    requester_id: uuid.UUID
    addressee_id: uuid.UUID
    status: str
    created_at: datetime
    responded_at: datetime | None = None
    requester_username: str | None = None

    class Config:
        from_attributes = True


class FriendDecisionRequest(BaseModel):
    action: str

    @validator("action")
    def validate_action(cls, value: str) -> str:
        normalized = value.lower()
        if normalized not in {"accept", "reject"}:
            raise ValueError("Action must be accept or reject")
        return normalized


class FriendResponse(BaseModel):
    id: uuid.UUID
    username: str

    class Config:
        from_attributes = True
