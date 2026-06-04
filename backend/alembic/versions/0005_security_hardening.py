# backend/alembic/versions/0005_security_hardening.py
"""Add security hardening tables

Revision ID: 0005_security_hardening
Revises: 0004_notification_prefs
Create Date: 2026-05-27 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005_security_hardening"
down_revision = "0004_notification_prefs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create MFA enums
    mfa_method = postgresql.ENUM(
        "totp",
        "sms",
        "email",
        "backup",
        name="mfamethod",
        create_type=False,
    )
    mfa_method.create(op.get_bind(), checkfirst=True)
    
    device_type = postgresql.ENUM(
        "web",
        "mobile",
        "desktop",
        "tablet",
        "other",
        name="devicetype",
        create_type=False,
    )
    device_type.create(op.get_bind(), checkfirst=True)
    
    session_status = postgresql.ENUM(
        "active",
        "revoked",
        "expired",
        name="sessionstatus",
        create_type=False,
    )
    session_status.create(op.get_bind(), checkfirst=True)
    
    login_status = postgresql.ENUM(
        "success",
        "failed",
        "mfa_pending",
        "blocked",
        name="loginstatus",
        create_type=False,
    )
    login_status.create(op.get_bind(), checkfirst=True)

    # MFA Setups table
    op.create_table(
        "mfa_setups",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("method", mfa_method, nullable=False),
        sa.Column("secret", sa.String(), nullable=True),
        sa.Column("phone_number", sa.String(), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("false"), index=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true"), index=True),
        sa.Column("backup_codes", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()"), index=True),
        sa.Column("verified_at", sa.DateTime(), nullable=True),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )

    # User Sessions table
    op.create_table(
        "user_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("device_id", sa.String(), nullable=False, index=True),
        sa.Column("device_name", sa.String(), nullable=True),
        sa.Column("device_type", device_type, nullable=False, server_default=sa.text("'web'")),
        sa.Column("browser", sa.String(), nullable=True),
        sa.Column("os", sa.String(), nullable=True),
        sa.Column("user_agent", sa.String(length=1024), nullable=True),
        sa.Column("ip_address", sa.String(), nullable=False, index=True),
        sa.Column("country", sa.String(), nullable=True),
        sa.Column("city", sa.String(), nullable=True),
        sa.Column("latitude", sa.String(), nullable=True),
        sa.Column("longitude", sa.String(), nullable=True),
        sa.Column("refresh_token_hash", sa.String(), nullable=False, index=True),
        sa.Column("access_token_hash", sa.String(), nullable=True),
        sa.Column("status", session_status, nullable=False, server_default=sa.text("'active'"), index=True),
        sa.Column("is_trusted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("mfa_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()"), index=True),
        sa.Column("last_activity_at", sa.DateTime(), nullable=False, server_default=sa.text("now()"), index=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False, index=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("revoke_reason", sa.String(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )

    # User Devices table
    op.create_table(
        "user_devices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("device_id", sa.String(), nullable=False, unique=True, index=True),
        sa.Column("device_name", sa.String(), nullable=True),
        sa.Column("device_type", device_type, nullable=False, server_default=sa.text("'web'")),
        sa.Column("fingerprint", sa.String(), nullable=True),
        sa.Column("is_trusted", sa.Boolean(), nullable=False, server_default=sa.text("false"), index=True),
        sa.Column("trust_token", sa.String(), nullable=True),
        sa.Column("last_seen_ip", sa.String(), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(), nullable=True),
        sa.Column("metadata", postgresql.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )

    # Login History table
    op.create_table(
        "login_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("status", login_status, nullable=False, index=True),
        sa.Column("method", sa.String(), nullable=False),
        sa.Column("identifier", sa.String(), nullable=False),
        sa.Column("device_id", sa.String(), nullable=True),
        sa.Column("device_name", sa.String(), nullable=True),
        sa.Column("user_agent", sa.String(length=1024), nullable=True),
        sa.Column("browser", sa.String(), nullable=True),
        sa.Column("os", sa.String(), nullable=True),
        sa.Column("ip_address", sa.String(), nullable=False, index=True),
        sa.Column("country", sa.String(), nullable=True),
        sa.Column("city", sa.String(), nullable=True),
        sa.Column("latitude", sa.String(), nullable=True),
        sa.Column("longitude", sa.String(), nullable=True),
        sa.Column("is_suspicious", sa.Boolean(), nullable=False, server_default=sa.text("false"), index=True),
        sa.Column("is_new_device", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_new_location", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("failure_reason", sa.String(), nullable=True),
        sa.Column("mfa_method_used", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()"), index=True),
    )

    # Suspicious Activities table
    op.create_table(
        "suspicious_activities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("activity_type", sa.String(), nullable=False),
        sa.Column("severity", sa.String(), nullable=False),
        sa.Column("ip_address", sa.String(), nullable=False, index=True),
        sa.Column("country", sa.String(), nullable=True),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("metadata", postgresql.JSON(), nullable=True),
        sa.Column("action_taken", sa.String(), nullable=True),
        sa.Column("is_resolved", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()"), index=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
    )

    # CSRF Tokens table
    op.create_table(
        "csrf_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("token_hash", sa.String(), nullable=False, unique=True, index=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_used", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("expires_at", sa.DateTime(), nullable=False, index=True),
        sa.Column("used_at", sa.DateTime(), nullable=True),
    )

    # IP Reputation table
    op.create_table(
        "ip_reputations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("ip_address", sa.String(), nullable=False, unique=True, index=True),
        sa.Column("reputation_score", sa.Float(), nullable=False, server_default=sa.text("0.0"), index=True),
        sa.Column("abuse_score", sa.Float(), nullable=False, server_default=sa.text("0.0")),
        sa.Column("is_vpn", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_proxy", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_datacenter", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_blacklisted", sa.Boolean(), nullable=False, server_default=sa.text("false"), index=True),
        sa.Column("failed_login_attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("successful_logins", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("suspicious_activities", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("country", sa.String(), nullable=True),
        sa.Column("city", sa.String(), nullable=True),
        sa.Column("latitude", sa.String(), nullable=True),
        sa.Column("longitude", sa.String(), nullable=True),
        sa.Column("timezone", sa.String(), nullable=True),
        sa.Column("isp", sa.String(), nullable=True),
        sa.Column("organization", sa.String(), nullable=True),
        sa.Column("metadata", postgresql.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )

    # Rate Limit Entries table
    op.create_table(
        "rate_limit_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("limit_key", sa.String(), nullable=False, index=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("expires_at", sa.DateTime(), nullable=False, index=True),
    )

    # Security Audit Logs table
    op.create_table(
        "security_audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("event_type", sa.String(), nullable=False, index=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(), nullable=True, index=True),
        sa.Column("user_agent", sa.String(length=1024), nullable=True),
        sa.Column("metadata", postgresql.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()"), index=True),
    )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table("security_audit_logs")
    op.drop_table("rate_limit_entries")
    op.drop_table("ip_reputations")
    op.drop_table("csrf_tokens")
    op.drop_table("suspicious_activities")
    op.drop_table("login_history")
    op.drop_table("user_devices")
    op.drop_table("user_sessions")
    op.drop_table("mfa_setups")
    
    # Drop enums
    op.execute("DROP TYPE IF EXISTS mfamethod")
    op.execute("DROP TYPE IF EXISTS devicetype")
    op.execute("DROP TYPE IF EXISTS sessionstatus")
    op.execute("DROP TYPE IF EXISTS loginstatus")
