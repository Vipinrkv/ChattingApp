"""Align existing deployed schema with current models.

Revision ID: 0002_align_existing_schema
Revises: 0001_initial_schema
Create Date: 2026-05-25 00:00:00.000000
"""
from alembic import op


revision = "0002_align_existing_schema"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR NOT NULL DEFAULT 'user'")
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_role ON users (role)")

    op.execute("ALTER TABLE messages ADD COLUMN IF NOT EXISTS media_url VARCHAR(2048)")
    op.execute("ALTER TABLE messages ADD COLUMN IF NOT EXISTS media_type VARCHAR(80)")
    op.execute("ALTER TABLE messages ADD COLUMN IF NOT EXISTS media_name VARCHAR(255)")
    op.execute("ALTER TABLE messages ADD COLUMN IF NOT EXISTS media_size INTEGER")
    op.execute("ALTER TABLE messages ADD COLUMN IF NOT EXISTS reply_to_message_id UUID")
    op.execute("ALTER TABLE messages ADD COLUMN IF NOT EXISTS reactions JSON NOT NULL DEFAULT '{}'::json")
    op.execute("ALTER TABLE messages ADD COLUMN IF NOT EXISTS is_pinned BOOLEAN NOT NULL DEFAULT false")
    op.execute("ALTER TABLE messages ADD COLUMN IF NOT EXISTS edited_at TIMESTAMP WITH TIME ZONE")

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'messages_reply_to_message_id_fkey'
            ) THEN
                ALTER TABLE messages
                ADD CONSTRAINT messages_reply_to_message_id_fkey
                FOREIGN KEY (reply_to_message_id)
                REFERENCES messages(id)
                ON DELETE SET NULL;
            END IF;
        END
        $$;
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_messages_reply_to_message_id ON messages (reply_to_message_id)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_messages_conversation ON messages (sender_id, receiver_id, timestamp)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_messages_receiver_conversation ON messages (receiver_id, sender_id, timestamp)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_messages_receiver_conversation")
    op.execute("DROP INDEX IF EXISTS ix_messages_conversation")
    op.execute("DROP INDEX IF EXISTS ix_messages_reply_to_message_id")
    op.execute("ALTER TABLE messages DROP CONSTRAINT IF EXISTS messages_reply_to_message_id_fkey")
    op.execute("ALTER TABLE messages DROP COLUMN IF EXISTS edited_at")
    op.execute("ALTER TABLE messages DROP COLUMN IF EXISTS is_pinned")
    op.execute("ALTER TABLE messages DROP COLUMN IF EXISTS reactions")
    op.execute("ALTER TABLE messages DROP COLUMN IF EXISTS reply_to_message_id")
    op.execute("ALTER TABLE messages DROP COLUMN IF EXISTS media_size")
    op.execute("ALTER TABLE messages DROP COLUMN IF EXISTS media_name")
    op.execute("ALTER TABLE messages DROP COLUMN IF EXISTS media_type")
    op.execute("ALTER TABLE messages DROP COLUMN IF EXISTS media_url")
    op.execute("DROP INDEX IF EXISTS ix_users_role")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS role")
