"""Add chat system advancement tables for 9 new features

Revision ID: 0008_chat_system_advancement
Revises: 0007_ai_moderation
Create Date: 2026-05-29 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0008_chat_system_advancement"
down_revision = "0007_ai_moderation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enums for new features
    message_status = postgresql.ENUM(
        "pending",
        "scheduled",
        "sent",
        "failed",
        name="messagestatus",
        create_type=False,
    )
    message_status.create(op.get_bind(), checkfirst=True)

    backup_status = postgresql.ENUM(
        "pending",
        "in_progress",
        "completed",
        "failed",
        name="backupstatus",
        create_type=False,
    )
    backup_status.create(op.get_bind(), checkfirst=True)

    sync_status = postgresql.ENUM(
        "synced",
        "pending",
        "failed",
        name="syncstatus",
        create_type=False,
    )
    sync_status.create(op.get_bind(), checkfirst=True)

    # 1. Message Bookmarks table
    op.create_table(
        "message_bookmarks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("bookmark_label", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"), index=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "message_id", name="uq_bookmark_user_message"),
    )

    # 2. Scheduled Messages table
    op.create_table(
        "scheduled_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("sender_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("receiver_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("content", sa.String(4096), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("status", message_status, nullable=False, server_default=sa.text("'scheduled'"), index=True),
        sa.Column("media_url", sa.String(2048), nullable=True),
        sa.Column("media_type", sa.String(80), nullable=True),
        sa.Column("error_message", sa.String(1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"), index=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["sender_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["receiver_id"], ["users.id"], ondelete="CASCADE"),
    )

    # 3. Message Translations table (cache)
    op.create_table(
        "message_translations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("source_language", sa.String(10), nullable=False),
        sa.Column("target_language", sa.String(10), nullable=False),
        sa.Column("translated_content", sa.String(4096), nullable=False),
        sa.Column("is_auto_translated", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("message_id", "target_language", name="uq_translation_message_language"),
    )

    # 4. Device Sync table
    op.create_table(
        "device_syncs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("device_id", sa.String(255), nullable=False, index=True),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("sync_status", sync_status, nullable=False, server_default=sa.text("'pending'"), index=True),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"), index=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("device_id", "message_id", name="uq_sync_device_message"),
    )

    # 5. Chat Backups table
    op.create_table(
        "chat_backups",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("backup_name", sa.String(255), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("message_count", sa.Integer(), nullable=False),
        sa.Column("backup_status", backup_status, nullable=False, server_default=sa.text("'pending'"), index=True),
        sa.Column("storage_path", sa.String(1024), nullable=True),
        sa.Column("storage_url", sa.String(2048), nullable=True),
        sa.Column("format", sa.String(20), nullable=False, server_default=sa.text("'json'"), index=True),
        sa.Column("error_message", sa.String(1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"), index=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )

    # 6. Shared Media Galleries table
    op.create_table(
        "shared_media_galleries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("conversation_id", sa.String(255), nullable=False, index=True),
        sa.Column("creator_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.String(1024), nullable=True),
        sa.Column("media_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("is_shared", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"), index=True),
        sa.ForeignKeyConstraint(["creator_id"], ["users.id"], ondelete="CASCADE"),
    )

    # 7. Gallery Media Items table
    op.create_table(
        "gallery_media_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("gallery_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("media_url", sa.String(2048), nullable=False),
        sa.Column("media_type", sa.String(80), nullable=False),
        sa.Column("media_size", sa.Integer(), nullable=True),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"), index=True),
        sa.ForeignKeyConstraint(["gallery_id"], ["shared_media_galleries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="CASCADE"),
    )

    # 8. AI Smart Replies table (suggestions)
    op.create_table(
        "ai_smart_replies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("reply_text", sa.String(4096), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("was_used", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"), index=True),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )

    # 9. Voice Transcriptions table
    op.create_table(
        "voice_transcriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("audio_url", sa.String(2048), nullable=False),
        sa.Column("transcribed_text", sa.String(4096), nullable=True),
        sa.Column("source_language", sa.String(10), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("is_processed", sa.Boolean(), nullable=False, server_default=sa.text("false"), index=True),
        sa.Column("processing_error", sa.String(1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"), index=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="CASCADE"),
    )

    # Add end-to-end encryption columns to messages table (optional encryption metadata)
    op.add_column("messages", sa.Column("is_encrypted", sa.Boolean(), nullable=False, server_default=sa.text("false"), index=True))
    op.add_column("messages", sa.Column("encryption_version", sa.String(20), nullable=True))

    # Create indexes for better query performance
    op.create_index("ix_scheduled_messages_scheduled_for_status", "scheduled_messages", ["scheduled_for", "status"])
    op.create_index("ix_device_syncs_status", "device_syncs", ["user_id", "sync_status"])
    op.create_index("ix_chat_backups_user_status", "chat_backups", ["user_id", "backup_status"])
    op.create_index("ix_ai_smart_replies_message", "ai_smart_replies", ["message_id", "confidence_score"])


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_ai_smart_replies_message")
    op.drop_index("ix_chat_backups_user_status")
    op.drop_index("ix_device_syncs_status")
    op.drop_index("ix_scheduled_messages_scheduled_for_status")

    # Drop columns from messages
    op.drop_column("messages", "encryption_version")
    op.drop_column("messages", "is_encrypted")

    # Drop tables in reverse order
    op.drop_table("voice_transcriptions")
    op.drop_table("ai_smart_replies")
    op.drop_table("gallery_media_items")
    op.drop_table("shared_media_galleries")
    op.drop_table("chat_backups")
    op.drop_table("device_syncs")
    op.drop_table("message_translations")
    op.drop_table("scheduled_messages")
    op.drop_table("message_bookmarks")

    # Drop enums
    op.execute("DROP TYPE syncstatus")
    op.execute("DROP TYPE backupstatus")
    op.execute("DROP TYPE messagestatus")
