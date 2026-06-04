"""Merge archive and advanced group migration heads

Revision ID: 0010_merge_archive_and_group_heads
Revises: 0006_add_message_archive_partitions, 0009_advanced_group_features
Create Date: 2026-06-01 00:00:00.000000
"""

revision = "0010_merge_archive_and_group_heads"
down_revision = ("0006_add_message_archive_partitions", "0009_advanced_group_features")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
