from pydantic import BaseModel
from typing import List
from uuid import UUID


class UserFeedControlResponse(BaseModel):
    user_id: UUID
    muted_words: List[str]
    ranking_mode: str
    sensitive_content_hidden: bool
    data_saver_enabled: bool

    class Config:
        from_attributes = True


class UserFeedControlUpdate(BaseModel):
    muted_words: List[str] | None = None
    ranking_mode: str | None = None
    sensitive_content_hidden: bool | None = None
    data_saver_enabled: bool | None = None
