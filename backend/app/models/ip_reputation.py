# backend/app/models/ip_reputation.py
from sqlalchemy import Column, String, Integer, Float, DateTime, Index, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSON
from datetime import datetime
from app.database.connection import Base
import uuid
import enum


class IPReputation(Base):
    """Track IP reputation and abuse scores"""
    __tablename__ = "ip_reputations"
    __table_args__ = (
        Index("ix_ip_reputations_ip_address", "ip_address"),
        Index("ix_ip_reputations_reputation_score", "reputation_score"),
        Index("ix_ip_reputations_updated_at", "updated_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ip_address = Column(String, unique=True, nullable=False)
    
    # Reputation metrics
    reputation_score = Column(Float, default=0.0)  # 0-1.0, higher = better
    abuse_score = Column(Float, default=0.0)  # 0-1.0, higher = worse
    
    # Flags
    is_vpn = Column(Boolean, default=False)
    is_proxy = Column(Boolean, default=False)
    is_datacenter = Column(Boolean, default=False)
    is_blacklisted = Column(Boolean, default=False, index=True)
    
    # Activity tracking
    failed_login_attempts = Column(Integer, default=0)
    successful_logins = Column(Integer, default=0)
    suspicious_activities = Column(Integer, default=0)
    
    # Geographic info
    country = Column(String, nullable=True)
    city = Column(String, nullable=True)
    latitude = Column(String, nullable=True)
    longitude = Column(String, nullable=True)
    timezone = Column(String, nullable=True)
    
    # ISP info
    isp = Column(String, nullable=True)
    organization = Column(String, nullable=True)
    
    # Metadata
    reputation_metadata = Column("metadata", JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RateLimitEntry(Base):
    """Rate limiting entries for protecting against abuse"""
    __tablename__ = "rate_limit_entries"
    __table_args__ = (
        Index("ix_rate_limit_entries_key", "limit_key"),
        Index("ix_rate_limit_entries_expires_at", "expires_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Rate limit key (ip:endpoint, user:endpoint, etc.)
    limit_key = Column(String, nullable=False)
    
    # Count and window
    attempt_count = Column(Integer, default=1)
    max_attempts = Column(Integer, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
