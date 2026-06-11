# c:\Users\Vipin\OneDrive\Desktop\WebAplications\ChattingApp\backend\app\schemas\group_schema.py
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, validator

DEFAULT_GROUP_TEMPLATES = {
    "study-circle": {
        "name": "Study Circle",
        "description": "A focused cohort for questions, resources, and weekly goals.",
        "category": "Education",
        "tags": ["study", "resources", "accountability"],
        "onboarding_steps": [
            {"title": "Introduce yourself", "body": "Share what you are learning and your weekly target."},
            {"title": "Pick a study lane", "body": "Choose a topic thread and add one useful resource."},
        ],
        "welcome_message": "Welcome in. Start with your current goal and one thing you need help with.",
        "growth_goal": 50,
    },
    "product-community": {
        "name": "Product Community",
        "description": "A customer community for updates, feedback, and support.",
        "category": "Product",
        "tags": ["feedback", "updates", "support"],
        "onboarding_steps": [
            {"title": "Read the announcement channel", "body": "Catch up on the latest product notes."},
            {"title": "Post your use case", "body": "Tell the group what you are building or solving."},
        ],
        "welcome_message": "Thanks for joining. Tell us your use case so the right people can help.",
        "growth_goal": 250,
    },
    "local-events": {
        "name": "Local Events Hub",
        "description": "A place to schedule meetups, sessions, and community activities.",
        "category": "Events",
        "tags": ["events", "meetups", "local"],
        "onboarding_steps": [
            {"title": "Set your availability", "body": "Share when you usually attend events."},
            {"title": "RSVP to an event", "body": "Open the events panel and join an upcoming activity."},
        ],
        "welcome_message": "Welcome. Check upcoming events and suggest one your community would enjoy.",
        "growth_goal": 120,
    },
}


class GroupCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: Optional[str] = Field(default=None, max_length=2000)
    type: str = Field(default="public")
    organization_name: Optional[str] = Field(default=None, max_length=160)
    category: Optional[str] = Field(default=None, max_length=80)
    tags: list[str] = Field(default_factory=list, max_items=8)
    is_discoverable: bool = True
    announcement_only: bool = False
    template_key: Optional[str] = Field(default=None, max_length=80)
    onboarding_steps: list[dict] = Field(default_factory=list, max_items=8)
    welcome_message: Optional[str] = Field(default=None, max_length=2000)
    growth_goal: int = Field(default=100, ge=1, le=1000000)

    @validator("type")
    def validate_type(cls, value: str) -> str:
        normalized = value.lower()
        if normalized not in {"public", "private", "anonymous", "organization"}:
            raise ValueError("Group type must be public, private, anonymous, or organization")
        return normalized


class GroupResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    type: str
    organization_name: Optional[str] = None
    category: Optional[str] = None
    tags: list[str] = []
    is_discoverable: bool = True
    is_verified: bool = False
    verification_status: str = "none"
    announcement_only: bool = False
    template_key: Optional[str] = None
    onboarding_steps: list[dict] = []
    welcome_message: Optional[str] = None
    growth_goal: int = 100
    created_by: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True


class GroupListResponse(GroupResponse):
    is_member: bool
    membership_status: Optional[str] = None
    member_count: int = 0
    message_count: int = 0
    event_count: int = 0
    discovery_score: float = 0


class GroupInviteRequest(BaseModel):
    user_id: uuid.UUID


class GroupSettingsRequest(BaseModel):
    category: Optional[str] = Field(default=None, max_length=80)
    tags: Optional[list[str]] = Field(default=None, max_items=8)
    is_discoverable: Optional[bool] = None
    announcement_only: Optional[bool] = None
    onboarding_steps: Optional[list[dict]] = Field(default=None, max_items=8)
    welcome_message: Optional[str] = Field(default=None, max_length=2000)
    growth_goal: Optional[int] = Field(default=None, ge=1, le=1000000)


class GroupMemberResponse(BaseModel):
    user_id: Optional[uuid.UUID] = None
    group_id: uuid.UUID
    role: str
    status: str
    alias: Optional[str] = None
    joined_at: datetime

    class Config:
        from_attributes = True


class GroupMessageCreateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class GroupMessageResponse(BaseModel):
    id: uuid.UUID
    sender_id: Optional[uuid.UUID] = None
    sender_alias: Optional[str] = None
    group_id: uuid.UUID
    content: str
    timestamp: datetime

    class Config:
        from_attributes = True


class GroupTemplateResponse(BaseModel):
    key: str
    name: str
    description: str
    category: str
    tags: list[str]
    onboarding_steps: list[dict]
    welcome_message: str
    growth_goal: int


class GroupEventCreateRequest(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    description: Optional[str] = Field(default=None, max_length=2000)
    starts_at: datetime
    ends_at: Optional[datetime] = None
    location: Optional[str] = Field(default=None, max_length=240)
    is_online: bool = True


class GroupEventResponse(BaseModel):
    id: uuid.UUID
    group_id: uuid.UUID
    host_id: uuid.UUID
    title: str
    description: Optional[str] = None
    starts_at: datetime
    ends_at: Optional[datetime] = None
    location: Optional[str] = None
    is_online: bool
    created_at: datetime

    class Config:
        from_attributes = True


class GroupAnalyticsResponse(BaseModel):
    group_id: uuid.UUID
    member_count: int
    invited_count: int
    message_count: int
    event_count: int
    days_active: int
    growth_goal: int
    growth_percent: float
    discovery_score: float
    engagement_rate: float
    onboarding_completion_estimate: float


class GroupMemberRoleUpdateRequest(BaseModel):
    role: str = Field(min_length=2, max_length=20)

    @validator("role")
    def validate_role(cls, value: str) -> str:
        normalized = value.lower()
        if normalized not in {"owner", "admin", "moderator", "member"}:
            raise ValueError("Role must be owner, admin, moderator, or member")
        return normalized
