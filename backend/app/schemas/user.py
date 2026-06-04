# c:\Users\Vipin\OneDrive\Desktop\WebAplications\ChattingApp\backend\app\schemas\user.py
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, validator


class UserRegisterRequest(BaseModel):
    phone: Optional[str] = Field(default=None, max_length=32)
    username: str = Field(min_length=3, max_length=50)

    @validator("username")
    def validate_username(cls, value: str) -> str:
        if not value.replace("_", "").isalnum():
            raise ValueError("Username may contain only letters, numbers, and underscores")
        return value


class UserCreate(BaseModel):
    phone: Optional[str] = None
    username: str = Field(min_length=3, max_length=50)
    email: Optional[str] = None
    bio: Optional[str] = None

    @validator("username")
    def validate_username(cls, value: str) -> str:
        if not value.replace("_", "").isalnum():
            raise ValueError("Username may contain only letters, numbers, and underscores")
        return value


class UserUpdate(BaseModel):
    phone: Optional[str] = None
    username: Optional[str] = Field(min_length=3, max_length=50)
    email: Optional[str] = None
    bio: Optional[str] = None

    @validator("username")
    def validate_username(cls, value: str) -> str:
        if value and not value.replace("_", "").isalnum():
            raise ValueError("Username may contain only letters, numbers, and underscores")
        return value


class UserResponse(BaseModel):
    id: uuid.UUID
    firebase_uid: str
    phone: Optional[str] = None
    username: str
    email: Optional[str] = None
    bio: Optional[str] = None
    role: str = "user"
    created_at: datetime

    class Config:
        from_attributes = True
