# backend/app/models/mfa.py
from sqlalchemy import Column, String, Boolean, DateTime, Index, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.connection import Base
import uuid
import enum


class MFAMethod(str, enum.Enum):
    """MFA method types"""
    TOTP = "totp"  # Time-based One-Time Password
    SMS = "sms"    # SMS verification
    EMAIL = "email"  # Email verification
    BACKUP = "backup"  # Backup codes


class MFASetup(Base):
    """User MFA configuration"""
    __tablename__ = "mfa_setups"
    __table_args__ = (
        Index("ix_mfa_setups_user_id", "user_id"),
        Index("ix_mfa_setups_created_at", "created_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    method = Column(SQLEnum(MFAMethod, values_callable=lambda x: [item.value for item in x]), nullable=False)
    secret = Column(String, nullable=True)  # Encrypted TOTP secret
    phone_number = Column(String, nullable=True)  # For SMS
    is_verified = Column(Boolean, default=False, index=True)
    is_active = Column(Boolean, default=True, index=True)
    backup_codes = Column(String, nullable=True)  # JSON of encrypted backup codes
    created_at = Column(DateTime, default=datetime.utcnow)
    verified_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
