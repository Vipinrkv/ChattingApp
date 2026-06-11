# backend/app/models/login_history.py
from sqlalchemy import Column, String, Boolean, DateTime, Index, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSON
from datetime import datetime
from app.database.connection import Base
import uuid
import enum


class LoginStatus(str, enum.Enum):
    """Login attempt status"""
    SUCCESS = "success"
    FAILED = "failed"
    MFA_PENDING = "mfa_pending"
    BLOCKED = "blocked"


class LoginHistory(Base):
    """Track all login attempts for audit and security"""
    __tablename__ = "login_history"
    __table_args__ = (
        Index("ix_login_history_user_id", "user_id"),
        Index("ix_login_history_status", "status"),
        Index("ix_login_history_created_at", "created_at"),
        Index("ix_login_history_ip_address", "ip_address"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=True)
    
    # Login attempt info
    status = Column(SQLEnum(LoginStatus), nullable=False)
    method = Column(String, nullable=False)  # 'email', 'phone', 'oauth', etc.
    identifier = Column(String, nullable=False)  # email or phone used
    
    # Device info
    device_id = Column(String, nullable=True)
    device_name = Column(String, nullable=True)
    user_agent = Column(String(1024), nullable=True)
    browser = Column(String, nullable=True)
    os = Column(String, nullable=True)
    
    # Network info
    ip_address = Column(String, nullable=False)
    country = Column(String, nullable=True)
    city = Column(String, nullable=True)
    latitude = Column(String, nullable=True)
    longitude = Column(String, nullable=True)
    
    # Security flags
    is_suspicious = Column(Boolean, default=False, index=True)
    is_new_device = Column(Boolean, default=False)
    is_new_location = Column(Boolean, default=False)
    
    # Additional details
    failure_reason = Column(String, nullable=True)
    mfa_method_used = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class SuspiciousActivity(Base):
    """Track suspicious login and access attempts"""
    __tablename__ = "suspicious_activities"
    __table_args__ = (
        Index("ix_suspicious_activities_user_id", "user_id"),
        Index("ix_suspicious_activities_ip_address", "ip_address"),
        Index("ix_suspicious_activities_created_at", "created_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=True)
    
    # Activity type
    activity_type = Column(String, nullable=False)  # 'brute_force', 'unusual_login', etc.
    severity = Column(String, nullable=False)  # 'low', 'medium', 'high', 'critical'
    
    # Network info
    ip_address = Column(String, nullable=False)
    country = Column(String, nullable=True)
    
    # Details
    description = Column(String, nullable=False)
    activity_metadata = Column("metadata", JSON, nullable=True)
    
    # Response
    action_taken = Column(String, nullable=True)  # 'none', 'block', 'challenge', etc.
    is_resolved = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
