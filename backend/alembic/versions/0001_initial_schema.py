# backend/alembic/versions/0001_initial_schema.py
"""Initial schema

Revision ID: 0001_initial_schema
Revises: None
Create Date: 2026-05-20 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0001_initial_schema"
down_revision = None
branch_labels = None
default_schema = None


def upgrade() -> None:
    friend_request_status = postgresql.ENUM(
        "pending",
        "accepted",
        "declined",
        name="friendrequeststatus",
        create_type=True,
    )
    friend_request_status.create(op.get_bind(), checkfirst=True)

    post_visibility = postgresql.ENUM(
        "public",
        "friends",
        "followers",
        "custom",
        name="postvisibility",
        create_type=True,
    )
    post_visibility.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("firebase_uid", sa.String(), nullable=False, unique=True, index=True),
        sa.Column("phone", sa.String(), nullable=True, unique=True, index=True),
        sa.Column("username", sa.String(), nullable=False, unique=True, index=True),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("bio", sa.String(), nullable=True),
        sa.Column("role", sa.String(), nullable=False, server_default=sa.text("'user'")),
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Index("ix_users_created_at", "created_at"),
        sa.Index("ix_users_role", "role"),
    )

    op.create_table(
        "groups",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=120), nullable=True, index=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("type", sa.String(length=30), nullable=True, index=True),
        sa.Column("organization_name", sa.String(length=160), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Index("ix_groups_created_by_type", "created_by", "type"),
        sa.Index("ix_groups_created_at", "created_at"),
    )

    op.create_table(
        "friends",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("requester_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("addressee_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("status", postgresql.ENUM("pending", "accepted", "declined", name="friendrequeststatus", create_type=False), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("responded_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "followers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("follower_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("following_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Index("ix_followers_follower_following", "follower_id", "following_id"),
        sa.Index("ix_followers_following_follower", "following_id", "follower_id"),
    )

    op.create_table(
        "blocks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("blocker_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("blocked_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("sender_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("receiver_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("content", sa.String(length=4096), nullable=True),
        sa.Column("media_url", sa.String(length=2048), nullable=True),
        sa.Column("media_type", sa.String(length=80), nullable=True),
        sa.Column("media_name", sa.String(length=255), nullable=True),
        sa.Column("media_size", sa.Integer(), nullable=True),
        sa.Column("reply_to_message_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("messages.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("reactions", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("is_pinned", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, index=True),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_seen", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Index("ix_messages_conversation", "sender_id", "receiver_id", "timestamp"),
        sa.Index("ix_messages_receiver_conversation", "receiver_id", "sender_id", "timestamp"),
    )

    op.create_table(
        "posts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("visibility", postgresql.ENUM("public", "friends", "followers", "custom", name="postvisibility", create_type=False), nullable=True, server_default="public"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Index("ix_posts_user_created_at", "user_id", "created_at"),
        sa.Index("ix_posts_visibility_created_at", "visibility", "created_at"),
    )

    op.create_table(
        "chat_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("peer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("is_muted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("user_id", "peer_id", name="uq_chat_settings_pair"),
        sa.CheckConstraint("user_id <> peer_id", name="ck_chat_settings_not_self"),
    )

    op.create_table(
        "group_members",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, nullable=False),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True, nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False, server_default=sa.text("'member'")),
        sa.Column("status", sa.String(length=20), nullable=True, index=True, server_default=sa.text("'active'")),
        sa.Column("alias", sa.String(length=80), nullable=True),
        sa.Column("invited_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("user_id", "group_id", name="uq_group_member_pair"),
    )

    op.create_table(
        "group_posts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Index("ix_group_posts_group_created_at", "group_id", "created_at"),
        sa.Index("ix_group_posts_user_created_at", "user_id", "created_at"),
    )

    op.create_table(
        "group_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("sender_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("content", sa.String(length=4096), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, index=True),
    )

    op.create_table(
        "post_comments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("post_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, index=True),
    )

    op.create_table(
        "post_likes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("post_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, index=True),
        sa.UniqueConstraint("post_id", "user_id", name="uq_post_likes_pair"),
    )

    op.create_table(
        "post_reposts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("post_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, index=True),
        sa.UniqueConstraint("post_id", "user_id", name="uq_post_reposts_pair"),
    )

    # Ensure alembic_version can support revision IDs longer than 32 characters
    op.execute("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(64);")



def downgrade() -> None:
    op.drop_table("post_reposts")
    op.drop_table("post_likes")
    op.drop_table("post_comments")
    op.drop_table("group_messages")
    op.drop_table("group_posts")
    op.drop_table("group_members")
    op.drop_table("chat_settings")
    op.drop_table("posts")
    op.drop_table("messages")
    op.drop_table("blocks")
    op.drop_table("followers")
    op.drop_table("friends")
    op.drop_table("groups")
    op.drop_table("users")

    post_visibility = postgresql.ENUM(
        "public",
        "friends",
        "followers",
        "custom",
        name="postvisibility",
    )
    post_visibility.drop(op.get_bind(), checkfirst=True)

    friend_request_status = postgresql.ENUM(
        "pending",
        "accepted",
        "declined",
        name="friendrequeststatus",
    )
    friend_request_status.drop(op.get_bind(), checkfirst=True)
