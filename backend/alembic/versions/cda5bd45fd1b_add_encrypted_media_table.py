"""add encrypted media table

Revision ID: cda5bd45fd1b
Revises: 0013_feed_polish_and_social_features
Create Date: 2026-06-14 00:50:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'cda5bd45fd1b'
down_revision = '0013_feed_polish_and_social_features'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "encrypted_media",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("messages.id", ondelete="CASCADE"), nullable=True),
        sa.Column("post_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("posts.id", ondelete="CASCADE"), nullable=True),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("media_type", sa.String(length=80), nullable=False),
        sa.Column("encrypted_data", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_encrypted_media_message_id", "encrypted_media", ["message_id"])
    op.create_index("ix_encrypted_media_post_id", "encrypted_media", ["post_id"])


def downgrade():
    op.drop_index("ix_encrypted_media_post_id", table_name="encrypted_media")
    op.drop_index("ix_encrypted_media_message_id", table_name="encrypted_media")
    op.drop_table("encrypted_media")
