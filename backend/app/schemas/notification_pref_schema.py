from pydantic import BaseModel
from typing import Dict, Any


class NotificationPreferencesResponse(BaseModel):
    preferences: Dict[str, Any]


class NotificationPreferencesUpdate(BaseModel):
    preferences: Dict[str, Any]
