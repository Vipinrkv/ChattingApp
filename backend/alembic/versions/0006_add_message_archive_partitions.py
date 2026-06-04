"""Add archive partitioning for historical messages

Revision ID: 0006_add_message_archive_partitions
Revises: 0005_security_hardening
Create Date: 2026-05-28 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0006_add_message_archive_partitions"
down_revision = "0005_security_hardening"
branch_labels = None
default_schema = None


def upgrade() -> None:
    op.execute(
        "CREATE TABLE IF NOT EXISTS message_archives ("
        "id UUID NOT NULL, "
        "sender_id UUID REFERENCES users(id) ON DELETE CASCADE, "
        "receiver_id UUID REFERENCES users(id) ON DELETE CASCADE, "
        "content VARCHAR(4096), "
        "media_url VARCHAR(2048), "
        "media_type VARCHAR(80), "
        "media_name VARCHAR(255), "
        "media_size INTEGER, "
        "reply_to_message_id UUID, "
        "reactions JSON NOT NULL DEFAULT '{}'::json, "
        "is_pinned BOOLEAN NOT NULL DEFAULT false, "
        "timestamp TIMESTAMPTZ NOT NULL DEFAULT now(), "
        "edited_at TIMESTAMPTZ, "
        "is_seen BOOLEAN NOT NULL DEFAULT false"
        ") PARTITION BY RANGE (timestamp)"
    )
    op.execute(
        "CREATE TABLE IF NOT EXISTS message_archives_2026 PARTITION OF message_archives "
        "FOR VALUES FROM ('2026-01-01') TO ('2027-01-01')"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_message_archives_id "
        "ON message_archives (id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_message_archives_sender_receiver_timestamp "
        "ON message_archives (sender_id, receiver_id, timestamp)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_message_archives_receiver_sender_timestamp "
        "ON message_archives (receiver_id, sender_id, timestamp)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS message_archives_2026")
    op.execute("DROP TABLE IF EXISTS message_archives")
