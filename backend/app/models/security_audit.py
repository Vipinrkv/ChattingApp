# backend/app/models/security_audit.py
from sqlalchemy import Column, String, DateTime, Index, Text
from sqlalchemy.dialects.postgresql import UUID, JSON
from datetime import datetime
from app.database.connection import Base
import uuid


class SecurityAudit(Base):
    """Audit log for all security-relevant events"""
    __tablename__ = "security_audit_logs"
    __table_args__ = (
        Index("ix_security_audit_user_id", "user_id"),
        Index("ix_security_audit_event_type", "event_type"),
        Index("ix_security_audit_created_at", "created_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    
    # Event info
    event_type = Column(String, nullable=False, index=True)
    # e.g., 'mfa_enabled', 'mfa_disabled', 'password_changed', 'session_revoked', 
    #       'device_trusted', 'suspicious_login', 'api_abuse', etc.
    
    # Details
    action = Column(String, nullable=False)  # 'created', 'updated', 'deleted', 'verified', etc.
    description = Column(Text, nullable=True)
    
    # Network info
    ip_address = Column(String, nullable=True, index=True)
    user_agent = Column(String(1024), nullable=True)
    
    # Additional metadata
    audit_metadata = Column("metadata", JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
