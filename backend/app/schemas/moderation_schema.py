from __future__ import annotations
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class ReportTargetType(str, Enum):
    user = "user"
    message = "message"
    post = "post"
    group_message = "group_message"
    group_post = "group_post"


class ReportStatus(str, Enum):
    open = "open"
    resolved = "resolved"
    dismissed = "dismissed"


class ModerationActionType(str, Enum):
    warning = "warning"
    mute = "mute"
    temporary_suspension = "temporary_suspension"
    permanent_ban = "permanent_ban"
    shadow_ban = "shadow_ban"
    unmute = "unmute"
    lift_suspension = "lift_suspension"
    content_removal = "content_removal"


class ReportEvidenceRequest(BaseModel):
    source_url: str = Field(..., min_length=1, max_length=1000)
    description: str | None = Field(default=None, max_length=1000)


class ReportEvidenceResponse(BaseModel):
    id: str
    source_url: str
    description: str | None
    created_at: str

    class Config:
        from_attributes = True


class ReportCreateRequest(BaseModel):
    target_type: ReportTargetType
    target_id: str
    reason: str = Field(..., min_length=10, max_length=500)
    details: str | None = Field(default=None, max_length=2000)
    evidence: list[ReportEvidenceRequest] = Field(default_factory=list)


class ReportResolutionRequest(BaseModel):
    action_type: ModerationActionType | None = None
    reason: str | None = Field(default=None, max_length=1000)
    duration_minutes: int | None = Field(default=None, ge=1, le=525600)
    comment: str | None = Field(default=None, max_length=2000)
    metadata: dict[str, Any] | None = None


class UserModerationActionRequest(BaseModel):
    action_type: ModerationActionType
    reason: str | None = Field(default=None, max_length=1000)
    duration_minutes: int | None = Field(default=None, ge=1, le=525600)
    metadata: dict[str, Any] | None = None


class ReportResponse(BaseModel):
    id: str
    reporter_id: str
    target_type: ReportTargetType
    target_id: str
    reason: str
    details: str | None
    status: ReportStatus
    review_notes: str | None
    reviewed_by: str | None
    reviewed_at: str | None
    created_at: str
    updated_at: str
    evidence: list[ReportEvidenceResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


class ModerationActionResponse(BaseModel):
    id: str
    moderator_id: str
    target_type: ReportTargetType
    target_id: str
    action_type: ModerationActionType
    reason: str | None
    metadata: dict[str, Any] | None
    created_at: str

    class Config:
        from_attributes = True
