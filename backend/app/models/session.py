# backend/app/models/session.py
from sqlalchemy import Column, String, Boolean, DateTime, Index, Integer, Enum as SQLEnum, Text
from sqlalchemy.dialects.postgresql import UUID, JSON
from datetime import datetime
from app.database.connection import Base
import uuid
import enum


class DeviceType(str, enum.Enum):
    """Device type categories"""
    WEB = "web"
    MOBILE = "mobile"
    DESKTOP = "desktop"
    TABLET = "tablet"
    OTHER = "other"


class SessionStatus(str, enum.Enum):
    """Session status"""
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"


class UserSession(Base):
    """User session and device tracking"""
    __tablename__ = "user_sessions"
    __table_args__ = (
        Index("ix_user_sessions_user_id", "user_id"),
        Index("ix_user_sessions_status", "status"),
        Index("ix_user_sessions_created_at", "created_at"),
        Index("ix_user_sessions_last_activity", "last_activity_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    
    # Device information
    device_id = Column(String, nullable=False, index=True)  # Unique device fingerprint
    device_name = Column(String, nullable=True)  # User-friendly device name
    device_type = Column(SQLEnum(DeviceType, values_callable=lambda x: [item.value for item in x]), default=DeviceType.WEB)
    
    # Browser/OS info
    browser = Column(String, nullable=True)
    os = Column(String, nullable=True)
    user_agent = Column(String(1024), nullable=True)
    
    # Network info
    ip_address = Column(String, nullable=False, index=True)
    country = Column(String, nullable=True)
    city = Column(String, nullable=True)
    latitude = Column(String, nullable=True)
    longitude = Column(String, nullable=True)
    
    # JWT tokens
    refresh_token_hash = Column(String, nullable=False, index=True)
    access_token_hash = Column(String, nullable=True)
    
    # Session management
    status = Column(SQLEnum(SessionStatus, values_callable=lambda x: [item.value for item in x]), default=SessionStatus.ACTIVE)
    is_trusted = Column(Boolean, default=False)  # User marked as trusted
    mfa_verified = Column(Boolean, default=False)  # MFA passed for this session
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False, index=True)
    revoked_at = Column(DateTime, nullable=True)
    revoke_reason = Column(String, nullable=True)
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UserDevice(Base):
    """User device fingerprints and trust status"""
    __tablename__ = "user_devices"
    __table_args__ = (
        Index("ix_user_devices_user_id", "user_id"),
        Index("ix_user_devices_device_id", "device_id"),
        Index("ix_user_devices_is_trusted", "is_trusted"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    device_id = Column(String, nullable=False, unique=True)
    device_name = Column(String, nullable=True)
    device_type = Column(SQLEnum(DeviceType, values_callable=lambda x: [item.value for item in x]), default=DeviceType.WEB)
    
    # Device fingerprint data (encrypted)
    fingerprint = Column(String, nullable=True)
    
    # Trust status
    is_trusted = Column(Boolean, default=False)
    trust_token = Column(String, nullable=True)  # Token for automatic trust
    
    # Last seen
    last_seen_ip = Column(String, nullable=True)
    last_seen_at = Column(DateTime, nullable=True)
    
    # Metadata
    device_metadata = Column("metadata", JSON, nullable=True)  # Browser, OS, etc.
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
