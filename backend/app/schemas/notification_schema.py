import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    actor_id: Optional[uuid.UUID] = None
    type: str
    text: Optional[str] = None
    data: dict
    is_read: bool
    timestamp: datetime

    class Config:
        from_attributes = True
