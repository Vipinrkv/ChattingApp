import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, JSON, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.database.connection import Base


class EnterpriseRole(Base):
    __tablename__ = "enterprise_roles"
    __table_args__ = (Index("ix_enterprise_roles_scope", "scope_type", "scope_id"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role_name = Column(String(80), nullable=False)
    scope_type = Column(String(40), default="platform", nullable=False)
    scope_id = Column(String(120), nullable=True)
    permissions = Column(JSON, default=list, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class AuditReview(Base):
    __tablename__ = "audit_reviews"
    __table_args__ = (Index("ix_audit_reviews_status_priority", "status", "priority"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    target_type = Column(String(80), nullable=False)
    target_id = Column(String(120), nullable=False)
    action = Column(String(120), nullable=False)
    status = Column(String(30), default="open", nullable=False)
    priority = Column(String(20), default="normal", nullable=False)
    metadata_json = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    reviewed_at = Column(DateTime, nullable=True)


class SupportTicket(Base):
    __tablename__ = "support_tickets"
    __table_args__ = (Index("ix_support_tickets_status_priority", "status", "priority"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    requester_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    subject = Column(String(180), nullable=False)
    body = Column(Text, nullable=True)
    status = Column(String(30), default="open", nullable=False)
    priority = Column(String(20), default="normal", nullable=False)
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class RevenueLedgerEntry(Base):
    __tablename__ = "revenue_ledger_entries"
    __table_args__ = (Index("ix_revenue_ledger_entries_source_created", "source_type", "created_at"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    source_type = Column(String(50), nullable=False)
    source_id = Column(String(120), nullable=True)
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    status = Column(String(30), default="booked", nullable=False)
    metadata_json = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class ReportingSnapshot(Base):
    __tablename__ = "reporting_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_key = Column(String(120), nullable=False, index=True)
    filters = Column(JSON, default=dict, nullable=False)
    payload = Column(JSON, default=dict, nullable=False)
    generated_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
