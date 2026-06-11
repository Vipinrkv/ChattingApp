"""Add feed event chain, user feed controls, user lists, and quote post columns

Revision ID: 0013_feed_polish_and_social_features
Revises: 0012_platform_enterprise_globalization
Create Date: 2026-06-11 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0013_feed_polish_and_social_features"
down_revision = "0012_platform_enterprise_globalization"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add quoted_post_id to posts table
    op.add_column("posts", sa.Column("quoted_post_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("posts.id", ondelete="SET NULL"), nullable=True))
    op.create_index("ix_posts_quoted_post_id", "posts", ["quoted_post_id"])

    # 2. Create feed_event_chain table
    op.create_table(
        "feed_event_chain",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("previous_hash", sa.String(64), nullable=True),
        sa.Column("hash", sa.String(64), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_feed_event_chain_timestamp", "feed_event_chain", ["timestamp"])
    op.create_index("ix_feed_event_chain_hash", "feed_event_chain", ["hash"])

    # 3. Create user_feed_controls table
    op.create_table(
        "user_feed_controls",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("muted_words", sa.JSON(), nullable=False),
        sa.Column("ranking_mode", sa.String(30), nullable=False, server_default="engagement"),
        sa.Column("sensitive_content_hidden", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("data_saver_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )

    # 4. Create user_lists and user_list_members tables
    op.create_table(
        "user_lists",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.String(250), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_user_lists_owner_id", "user_lists", ["owner_id"])

    op.create_table(
        "user_list_members",
        sa.Column("list_id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["list_id"], ["user_lists.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    op.drop_table("user_list_members")
    op.drop_index("ix_user_lists_owner_id", table_name="user_lists")
    op.drop_table("user_lists")
    op.drop_table("user_feed_controls")
    op.drop_index("ix_feed_event_chain_hash", table_name="feed_event_chain")
    op.drop_index("ix_feed_event_chain_timestamp", table_name="feed_event_chain")
    op.drop_table("feed_event_chain")
    op.drop_index("ix_posts_quoted_post_id", table_name="posts")
    op.drop_column("posts", "quoted_post_id")
