"""Add platform enterprise and globalization foundations

Revision ID: 0012_platform_enterprise_globalization
Revises: 0011_analytics_social_scaling
Create Date: 2026-06-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0012_platform_enterprise_globalization"
down_revision = "0011_analytics_social_scaling"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "live_streams",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("host_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(180), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="scheduled"),
        sa.Column("stream_key", sa.String(120), nullable=True),
        sa.Column("playback_url", sa.Text(), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("viewer_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["host_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_live_streams_host_id", "live_streams", ["host_id"])
    op.create_index("ix_live_streams_host_status", "live_streams", ["host_id", "status"])
    op.create_index("ix_live_streams_status", "live_streams", ["status"])

    op.create_table(
        "call_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("creator_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("room_id", sa.String(120), nullable=False),
        sa.Column("call_type", sa.String(20), nullable=False, server_default="video"),
        sa.Column("status", sa.String(30), nullable=False, server_default="waiting"),
        sa.Column("participant_ids", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("quality_score", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["creator_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_call_sessions_creator_id", "call_sessions", ["creator_id"])
    op.create_index("ix_call_sessions_creator_status", "call_sessions", ["creator_id", "status"])
    op.create_index("ix_call_sessions_room_id", "call_sessions", ["room_id"])
    op.create_index("ix_call_sessions_status", "call_sessions", ["status"])

    op.create_table(
        "screen_share_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("call_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("presenter_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="active"),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["call_session_id"], ["call_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["presenter_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_screen_share_sessions_call_session_id", "screen_share_sessions", ["call_session_id"])
    op.create_index("ix_screen_share_sessions_presenter_id", "screen_share_sessions", ["presenter_id"])

    op.create_table(
        "creator_monetization_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payout_status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("payout_provider", sa.String(50), nullable=True),
        sa.Column("revenue_share_bps", sa.Integer(), nullable=False, server_default="7000"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_creator_monetization_profiles_user_id", "creator_monetization_profiles", ["user_id"], unique=True)

    op.create_table(
        "marketplace_listings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("seller_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(180), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(80), nullable=True),
        sa.Column("price_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("status", sa.String(30), nullable=False, server_default="active"),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["seller_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_marketplace_listings_seller_id", "marketplace_listings", ["seller_id"])
    op.create_index("ix_marketplace_listings_status", "marketplace_listings", ["status"])
    op.create_index("ix_marketplace_listings_status_category", "marketplace_listings", ["status", "category"])

    op.create_table(
        "subscription_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("plan_type", sa.String(40), nullable=False, server_default="creator"),
        sa.Column("price_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("interval", sa.String(20), nullable=False, server_default="monthly"),
        sa.Column("features", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_subscription_plans_plan_type", "subscription_plans", ["plan_type"])

    op.create_table(
        "user_subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="active"),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("renews_at", sa.DateTime(), nullable=True),
        sa.Column("canceled_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["plan_id"], ["subscription_plans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_user_subscriptions_plan_id", "user_subscriptions", ["plan_id"])
    op.create_index("ix_user_subscriptions_user_id", "user_subscriptions", ["user_id"])
    op.create_index("ix_user_subscriptions_user_status", "user_subscriptions", ["user_id", "status"])

    op.create_table(
        "platform_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("host_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(180), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("starts_at", sa.DateTime(), nullable=False),
        sa.Column("ends_at", sa.DateTime(), nullable=True),
        sa.Column("event_type", sa.String(50), nullable=False, server_default="community"),
        sa.Column("access_level", sa.String(40), nullable=False, server_default="public"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["host_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_platform_events_host_id", "platform_events", ["host_id"])
    op.create_index("ix_platform_events_host_start", "platform_events", ["host_id", "starts_at"])
    op.create_index("ix_platform_events_starts_at", "platform_events", ["starts_at"])

    op.create_table(
        "community_channels",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("visibility", sa.String(30), nullable=False, server_default="public"),
        sa.Column("channel_type", sa.String(40), nullable=False, server_default="discussion"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_community_channels_owner_id", "community_channels", ["owner_id"])
    op.create_index("ix_community_channels_visibility", "community_channels", ["visibility", "created_at"])

    op.create_table(
        "enterprise_roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role_name", sa.String(80), nullable=False),
        sa.Column("scope_type", sa.String(40), nullable=False, server_default="platform"),
        sa.Column("scope_id", sa.String(120), nullable=True),
        sa.Column("permissions", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_enterprise_roles_user_id", "enterprise_roles", ["user_id"])
    op.create_index("ix_enterprise_roles_scope", "enterprise_roles", ["scope_type", "scope_id"])

    op.create_table(
        "audit_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_type", sa.String(80), nullable=False),
        sa.Column("target_id", sa.String(120), nullable=False),
        sa.Column("action", sa.String(120), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="open"),
        sa.Column("priority", sa.String(20), nullable=False, server_default="normal"),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_audit_reviews_actor_id", "audit_reviews", ["actor_id"])
    op.create_index("ix_audit_reviews_status_priority", "audit_reviews", ["status", "priority"])

    op.create_table(
        "support_tickets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("requester_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("subject", sa.String(180), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="open"),
        sa.Column("priority", sa.String(20), nullable=False, server_default="normal"),
        sa.Column("assigned_to", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["assigned_to"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["requester_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_support_tickets_requester_id", "support_tickets", ["requester_id"])
    op.create_index("ix_support_tickets_status_priority", "support_tickets", ["status", "priority"])

    op.create_table(
        "revenue_ledger_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("source_id", sa.String(120), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("status", sa.String(30), nullable=False, server_default="booked"),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_revenue_ledger_entries_user_id", "revenue_ledger_entries", ["user_id"])
    op.create_index("ix_revenue_ledger_entries_source_created", "revenue_ledger_entries", ["source_type", "created_at"])

    op.create_table(
        "reporting_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("report_key", sa.String(120), nullable=False),
        sa.Column("filters", sa.JSON(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("generated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["generated_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_reporting_snapshots_report_key", "reporting_snapshots", ["report_key"])

    op.create_table(
        "localization_strings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("locale", sa.String(16), nullable=False),
        sa.Column("message_key", sa.String(180), nullable=False),
        sa.Column("message_value", sa.Text(), nullable=False),
        sa.Column("namespace", sa.String(80), nullable=False, server_default="app"),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_localization_strings_locale", "localization_strings", ["locale"])
    op.create_index("ix_localization_strings_locale_key", "localization_strings", ["locale", "message_key"], unique=True)

    op.create_table(
        "user_locale_preferences",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("locale", sa.String(16), nullable=False, server_default="en-US"),
        sa.Column("timezone", sa.String(80), nullable=False, server_default="UTC"),
        sa.Column("region_code", sa.String(16), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_user_locale_preferences_region_code", "user_locale_preferences", ["region_code"])
    op.create_index("ix_user_locale_preferences_user_id", "user_locale_preferences", ["user_id"], unique=True)

    op.create_table(
        "regional_content_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("region_code", sa.String(16), nullable=False),
        sa.Column("policy_key", sa.String(120), nullable=False),
        sa.Column("policy_value", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_regional_content_policies_region_code", "regional_content_policies", ["region_code"])

    op.create_table(
        "international_moderation_queue",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("target_type", sa.String(80), nullable=False),
        sa.Column("target_id", sa.String(120), nullable=False),
        sa.Column("region_code", sa.String(16), nullable=False),
        sa.Column("locale", sa.String(16), nullable=True),
        sa.Column("reason", sa.String(180), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_international_moderation_region_status", "international_moderation_queue", ["region_code", "status"])

    op.create_table(
        "timezone_scheduled_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_type", sa.String(80), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("timezone", sa.String(80), nullable=False, server_default="UTC"),
        sa.Column("scheduled_for_utc", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="scheduled"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_timezone_scheduled_items_owner_id", "timezone_scheduled_items", ["owner_id"])
    op.create_index("ix_timezone_scheduled_items_due", "timezone_scheduled_items", ["status", "scheduled_for_utc"])

    op.create_table(
        "region_recommendations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("region_code", sa.String(16), nullable=False),
        sa.Column("target_type", sa.String(80), nullable=False),
        sa.Column("target_id", sa.String(120), nullable=False),
        sa.Column("score", sa.Numeric(8, 4), nullable=False),
        sa.Column("reason", sa.String(180), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_region_recommendations_region_score", "region_recommendations", ["region_code", "score"])


def downgrade() -> None:
    op.drop_index("ix_region_recommendations_region_score", table_name="region_recommendations")
    op.drop_table("region_recommendations")
    op.drop_index("ix_timezone_scheduled_items_due", table_name="timezone_scheduled_items")
    op.drop_index("ix_timezone_scheduled_items_owner_id", table_name="timezone_scheduled_items")
    op.drop_table("timezone_scheduled_items")
    op.drop_index("ix_international_moderation_region_status", table_name="international_moderation_queue")
    op.drop_table("international_moderation_queue")
    op.drop_index("ix_regional_content_policies_region_code", table_name="regional_content_policies")
    op.drop_table("regional_content_policies")
    op.drop_index("ix_user_locale_preferences_user_id", table_name="user_locale_preferences")
    op.drop_index("ix_user_locale_preferences_region_code", table_name="user_locale_preferences")
    op.drop_table("user_locale_preferences")
    op.drop_index("ix_localization_strings_locale_key", table_name="localization_strings")
    op.drop_index("ix_localization_strings_locale", table_name="localization_strings")
    op.drop_table("localization_strings")
    op.drop_index("ix_reporting_snapshots_report_key", table_name="reporting_snapshots")
    op.drop_table("reporting_snapshots")
    op.drop_index("ix_revenue_ledger_entries_source_created", table_name="revenue_ledger_entries")
    op.drop_index("ix_revenue_ledger_entries_user_id", table_name="revenue_ledger_entries")
    op.drop_table("revenue_ledger_entries")
    op.drop_index("ix_support_tickets_status_priority", table_name="support_tickets")
    op.drop_index("ix_support_tickets_requester_id", table_name="support_tickets")
    op.drop_table("support_tickets")
    op.drop_index("ix_audit_reviews_status_priority", table_name="audit_reviews")
    op.drop_index("ix_audit_reviews_actor_id", table_name="audit_reviews")
    op.drop_table("audit_reviews")
    op.drop_index("ix_enterprise_roles_scope", table_name="enterprise_roles")
    op.drop_index("ix_enterprise_roles_user_id", table_name="enterprise_roles")
    op.drop_table("enterprise_roles")
    op.drop_index("ix_community_channels_visibility", table_name="community_channels")
    op.drop_index("ix_community_channels_owner_id", table_name="community_channels")
    op.drop_table("community_channels")
    op.drop_index("ix_platform_events_starts_at", table_name="platform_events")
    op.drop_index("ix_platform_events_host_start", table_name="platform_events")
    op.drop_index("ix_platform_events_host_id", table_name="platform_events")
    op.drop_table("platform_events")
    op.drop_index("ix_user_subscriptions_user_status", table_name="user_subscriptions")
    op.drop_index("ix_user_subscriptions_user_id", table_name="user_subscriptions")
    op.drop_index("ix_user_subscriptions_plan_id", table_name="user_subscriptions")
    op.drop_table("user_subscriptions")
    op.drop_index("ix_subscription_plans_plan_type", table_name="subscription_plans")
    op.drop_table("subscription_plans")
    op.drop_index("ix_marketplace_listings_status_category", table_name="marketplace_listings")
    op.drop_index("ix_marketplace_listings_status", table_name="marketplace_listings")
    op.drop_index("ix_marketplace_listings_seller_id", table_name="marketplace_listings")
    op.drop_table("marketplace_listings")
    op.drop_index("ix_creator_monetization_profiles_user_id", table_name="creator_monetization_profiles")
    op.drop_table("creator_monetization_profiles")
    op.drop_index("ix_screen_share_sessions_presenter_id", table_name="screen_share_sessions")
    op.drop_index("ix_screen_share_sessions_call_session_id", table_name="screen_share_sessions")
    op.drop_table("screen_share_sessions")
    op.drop_index("ix_call_sessions_status", table_name="call_sessions")
    op.drop_index("ix_call_sessions_room_id", table_name="call_sessions")
    op.drop_index("ix_call_sessions_creator_status", table_name="call_sessions")
    op.drop_index("ix_call_sessions_creator_id", table_name="call_sessions")
    op.drop_table("call_sessions")
    op.drop_index("ix_live_streams_status", table_name="live_streams")
    op.drop_index("ix_live_streams_host_status", table_name="live_streams")
    op.drop_index("ix_live_streams_host_id", table_name="live_streams")
    op.drop_table("live_streams")
