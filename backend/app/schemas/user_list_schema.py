from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
from uuid import UUID


class UserListCreate(BaseModel):
    name: str
    description: Optional[str] = None


class UserListMemberAdd(BaseModel):
    user_id: UUID


class UserListResponse(BaseModel):
    id: UUID
    owner_id: UUID
    name: str
    description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class UserListMemberResponse(BaseModel):
    list_id: UUID
    user_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
