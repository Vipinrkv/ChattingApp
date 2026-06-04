"""Add advanced group feature fields and events

Revision ID: 0009_advanced_group_features
Revises: 0008_chat_system_advancement
Create Date: 2026-06-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0009_advanced_group_features"
down_revision = "0008_chat_system_advancement"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("groups", sa.Column("category", sa.String(80), nullable=True))
    op.add_column("groups", sa.Column("tags", sa.JSON(), nullable=True))
    op.add_column("groups", sa.Column("is_discoverable", sa.Boolean(), nullable=True))
    op.add_column("groups", sa.Column("is_verified", sa.Boolean(), nullable=True))
    op.add_column("groups", sa.Column("verification_status", sa.String(20), nullable=True))
    op.add_column("groups", sa.Column("announcement_only", sa.Boolean(), nullable=True))
    op.add_column("groups", sa.Column("template_key", sa.String(80), nullable=True))
    op.add_column("groups", sa.Column("onboarding_steps", sa.JSON(), nullable=True))
    op.add_column("groups", sa.Column("welcome_message", sa.Text(), nullable=True))
    op.add_column("groups", sa.Column("growth_goal", sa.Integer(), nullable=True))
    op.execute(
        "UPDATE groups SET "
        "tags = COALESCE(tags, '[]'::json), "
        "is_discoverable = COALESCE(is_discoverable, true), "
        "is_verified = COALESCE(is_verified, false), "
        "verification_status = COALESCE(verification_status, 'none'), "
        "announcement_only = COALESCE(announcement_only, false), "
        "onboarding_steps = COALESCE(onboarding_steps, '[]'::json), "
        "growth_goal = COALESCE(growth_goal, 100)"
    )
    op.alter_column("groups", "tags", nullable=False)
    op.alter_column("groups", "is_discoverable", nullable=False)
    op.alter_column("groups", "is_verified", nullable=False)
    op.alter_column("groups", "verification_status", nullable=False)
    op.alter_column("groups", "announcement_only", nullable=False)
    op.alter_column("groups", "onboarding_steps", nullable=False)
    op.alter_column("groups", "growth_goal", nullable=False)
    op.create_index("ix_groups_discovery", "groups", ["is_discoverable", "category", "created_at"])
    op.create_index("ix_groups_is_discoverable", "groups", ["is_discoverable"])
    op.create_index("ix_groups_is_verified", "groups", ["is_verified"])
    op.create_index("ix_groups_template_key", "groups", ["template_key"])
    op.create_index("ix_groups_verification_status", "groups", ["verification_status"])

    op.create_table(
        "group_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("host_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("location", sa.String(240), nullable=True),
        sa.Column("is_online", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["host_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_group_events_group_start", "group_events", ["group_id", "starts_at"])
    op.create_index("ix_group_events_host_start", "group_events", ["host_id", "starts_at"])


def downgrade() -> None:
    op.drop_index("ix_group_events_host_start", table_name="group_events")
    op.drop_index("ix_group_events_group_start", table_name="group_events")
    op.drop_table("group_events")

    op.drop_index("ix_groups_verification_status", table_name="groups")
    op.drop_index("ix_groups_template_key", table_name="groups")
    op.drop_index("ix_groups_is_verified", table_name="groups")
    op.drop_index("ix_groups_is_discoverable", table_name="groups")
    op.drop_index("ix_groups_discovery", table_name="groups")
    op.drop_column("groups", "growth_goal")
    op.drop_column("groups", "welcome_message")
    op.drop_column("groups", "onboarding_steps")
    op.drop_column("groups", "template_key")
    op.drop_column("groups", "announcement_only")
    op.drop_column("groups", "verification_status")
    op.drop_column("groups", "is_verified")
    op.drop_column("groups", "is_discoverable")
    op.drop_column("groups", "tags")
    op.drop_column("groups", "category")
