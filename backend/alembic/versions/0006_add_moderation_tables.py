"""Add moderation tables and user moderation fields

Revision ID: 0006_add_moderation_tables
Revises: 0005_security_hardening
Create Date: 2026-05-28 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0006_add_moderation_tables"
down_revision = "0005_security_hardening"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_shadow_banned", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "users",
        sa.Column("is_muted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "users",
        sa.Column("muted_until", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("is_suspended", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "users",
        sa.Column("suspended_until", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_users_is_shadow_banned", "users", ["is_shadow_banned"])
    op.create_index("ix_users_is_muted", "users", ["is_muted"])
    op.create_index("ix_users_is_suspended", "users", ["is_suspended"])

    op.create_table(
        "reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("reporter_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_type", sa.String(), nullable=False),
        sa.Column("target_id", sa.String(), nullable=False),
        sa.Column("reason", sa.String(), nullable=False),
        sa.Column("details", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default=sa.text("'open'")),
        sa.Column("review_notes", sa.String(), nullable=True),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Index("ix_reports_reporter_id", "reporter_id"),
        sa.Index("ix_reports_target_type", "target_type"),
        sa.Index("ix_reports_target_id", "target_id"),
        sa.Index("ix_reports_status", "status"),
    )

    op.create_table(
        "report_evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_url", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "moderation_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("moderator_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_type", sa.String(), nullable=False),
        sa.Column("target_id", sa.String(), nullable=False),
        sa.Column("action_type", sa.String(), nullable=False),
        sa.Column("reason", sa.String(), nullable=True),
        sa.Column("metadata", postgresql.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("moderation_actions")
    op.drop_table("report_evidence")
    op.drop_table("reports")
    op.drop_index("ix_users_is_suspended", table_name="users")
    op.drop_index("ix_users_is_muted", table_name="users")
    op.drop_index("ix_users_is_shadow_banned", table_name="users")
    op.drop_column("users", "suspended_until")
    op.drop_column("users", "is_suspended")
    op.drop_column("users", "muted_until")
    op.drop_column("users", "is_muted")
    op.drop_column("users", "is_shadow_banned")
