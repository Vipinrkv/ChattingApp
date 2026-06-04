"""Add analytics and advanced social feature foundations

Revision ID: 0011_analytics_social_scaling
Revises: 0010_merge_archive_and_group_heads
Create Date: 2026-06-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0011_analytics_social_scaling"
down_revision = "0010_merge_archive_and_group_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("users", sa.Column("verification_badge", sa.String(), nullable=True))

    op.create_table(
        "analytics_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_name", sa.String(80), nullable=False),
        sa.Column("entity_type", sa.String(80), nullable=True),
        sa.Column("entity_id", sa.String(120), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_analytics_events_entity", "analytics_events", ["entity_type", "entity_id"])
    op.create_index("ix_analytics_events_event_name", "analytics_events", ["event_name"])
    op.create_index("ix_analytics_events_name_created_at", "analytics_events", ["event_name", "created_at"])
    op.create_index("ix_analytics_events_user_created_at", "analytics_events", ["user_id", "created_at"])

    op.create_table(
        "close_friends",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("friend_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["friend_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_close_friends_owner_friend", "close_friends", ["owner_id", "friend_id"], unique=True)

    op.create_table(
        "polls",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question", sa.String(240), nullable=False),
        sa.Column("options", sa.JSON(), nullable=False),
        sa.Column("votes", sa.JSON(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_polls_owner_created_at", "polls", ["owner_id", "created_at"])

    op.create_table(
        "stories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("media_url", sa.Text(), nullable=False),
        sa.Column("caption", sa.String(240), nullable=True),
        sa.Column("audience", sa.String(40), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_stories_owner_expires_at", "stories", ["owner_id", "expires_at"])

    op.create_table(
        "short_videos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("video_url", sa.Text(), nullable=False),
        sa.Column("thumbnail_url", sa.Text(), nullable=True),
        sa.Column("caption", sa.String(240), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_short_videos_owner_created_at", "short_videos", ["owner_id", "created_at"])

    op.create_table(
        "verification_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_verification_requests_user_status", "verification_requests", ["user_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_verification_requests_user_status", table_name="verification_requests")
    op.drop_table("verification_requests")
    op.drop_index("ix_short_videos_owner_created_at", table_name="short_videos")
    op.drop_table("short_videos")
    op.drop_index("ix_stories_owner_expires_at", table_name="stories")
    op.drop_table("stories")
    op.drop_index("ix_polls_owner_created_at", table_name="polls")
    op.drop_table("polls")
    op.drop_index("ix_close_friends_owner_friend", table_name="close_friends")
    op.drop_table("close_friends")
    op.drop_index("ix_analytics_events_user_created_at", table_name="analytics_events")
    op.drop_index("ix_analytics_events_name_created_at", table_name="analytics_events")
    op.drop_index("ix_analytics_events_event_name", table_name="analytics_events")
    op.drop_index("ix_analytics_events_entity", table_name="analytics_events")
    op.drop_table("analytics_events")
    op.drop_column("users", "verification_badge")
    op.drop_column("users", "is_verified")
