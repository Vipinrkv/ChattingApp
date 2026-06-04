"""Add notifications table

Revision ID: 0003_add_notifications_table
Revises: 0002_align_existing_schema
Create Date: 2026-05-25 00:30:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0003_add_notifications_table"
down_revision = "0002_align_existing_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("type", sa.String(length=80), nullable=False),
        sa.Column("text", sa.String(length=1024), nullable=True),
        sa.Column("data", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, index=True),
    )
    op.create_index("ix_notifications_user_timestamp", "notifications", ["user_id", "timestamp"]) 
    op.create_index("ix_notifications_is_read", "notifications", ["is_read"]) 


def downgrade() -> None:
    op.drop_index("ix_notifications_is_read", table_name="notifications")
    op.drop_index("ix_notifications_user_timestamp", table_name="notifications")
    op.drop_table("notifications")
