import uuid
from datetime import datetime
from sqlalchemy import Column, ForeignKey, DateTime, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from app.database.connection import Base


class PostRepost(Base):
    __tablename__ = "post_reposts"
    __table_args__ = (
        UniqueConstraint("post_id", "user_id", name="uq_post_reposts_pair"),
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    post_id = Column(PG_UUID(as_uuid=True), ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
