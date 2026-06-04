from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from enum import Enum


class PostVisibility(str, Enum):
    PUBLIC = "public"
    FRIENDS = "friends"
    FOLLOWERS = "followers"
    CUSTOM = "custom"


class PostCreate(BaseModel):
    content: str
    visibility: PostVisibility = PostVisibility.PUBLIC


class PostUpdate(BaseModel):
    content: Optional[str] = None
    visibility: Optional[PostVisibility] = None


class PostResponse(BaseModel):
    id: str
    user_id: str
    content: str
    visibility: PostVisibility
    created_at: datetime

    class Config:
        from_attributes = True


class GroupPostCreate(BaseModel):
    content: str


class GroupPostResponse(BaseModel):
    id: str
    group_id: str
    user_id: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True
