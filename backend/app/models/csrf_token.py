# backend/app/models/csrf_token.py
from sqlalchemy import Column, String, DateTime, Index, Boolean
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from app.database.connection import Base
import uuid


class CSRFToken(Base):
    """CSRF token storage for double-submit cookie pattern"""
    __tablename__ = "csrf_tokens"
    __table_args__ = (
        Index("ix_csrf_tokens_user_id", "user_id"),
        Index("ix_csrf_tokens_token_hash", "token_hash"),
        Index("ix_csrf_tokens_expires_at", "expires_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    
    # Token info
    token_hash = Column(String, nullable=False, unique=True, index=True)
    session_id = Column(UUID(as_uuid=True), nullable=True)  # Optional: tie to session
    
    # Status
    is_used = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False, index=True)
    used_at = Column(DateTime, nullable=True)
