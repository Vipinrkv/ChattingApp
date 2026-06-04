from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class EnterpriseRoleCreate(BaseModel):
    user_id: UUID
    role_name: str = Field(min_length=1, max_length=80)
    scope_type: str = "platform"
    scope_id: str | None = None
    permissions: list[str] = Field(default_factory=list)


class SupportTicketCreate(BaseModel):
    subject: str = Field(min_length=1, max_length=180)
    body: str | None = None
    priority: str = "normal"


class AuditReviewCreate(BaseModel):
    target_type: str = Field(min_length=1, max_length=80)
    target_id: str = Field(min_length=1, max_length=120)
    action: str = Field(min_length=1, max_length=120)
    priority: str = "normal"
    metadata: dict[str, object] = Field(default_factory=dict)


class RevenueLedgerEntryCreate(BaseModel):
    user_id: UUID | None = None
    source_type: str = Field(min_length=1, max_length=50)
    source_id: str | None = None
    amount: Decimal
    currency: str = Field(default="USD", min_length=3, max_length=3)
    status: str = "booked"
    metadata: dict[str, object] = Field(default_factory=dict)


class EnterpriseSummary(BaseModel):
    roles: int
    open_audit_reviews: int
    open_support_tickets: int
    booked_revenue: float
    reporting_snapshots: int
    moderation_queue: int
    generated_at: datetime
