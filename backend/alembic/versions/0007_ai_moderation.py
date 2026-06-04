"""Add AI moderation and community moderation tables

Revision ID: 0007_ai_moderation
Revises: 0006_add_moderation_tables
Create Date: 2026-05-28 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0007_ai_moderation'
down_revision = '0006_add_moderation_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create ai_moderation_results table
    op.create_table(
        'ai_moderation_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('content_id', sa.String(255), nullable=False),
        sa.Column('content_type', sa.String(50), nullable=False),
        sa.Column('content_text', sa.Text(), nullable=False),
        sa.Column('toxicity_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('severe_toxicity_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('identity_attack_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('insult_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('profanity_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('threat_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('is_spam', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_nsfw', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('has_harmful_links', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_phishing', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('overall_risk_level', sa.String(20), nullable=False, server_default='low'),
        sa.Column('should_auto_moderate', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('recommended_action', sa.String(50), nullable=False, server_default='none'),
        sa.Column('confidence_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('detected_issues', postgresql.JSON(), nullable=False, server_default='{}'),
        sa.Column('analysis_metadata', postgresql.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_content_type_risk', 'ai_moderation_results', ['content_type', 'overall_risk_level'])
    op.create_index('idx_ai_created_at', 'ai_moderation_results', ['created_at'])
    op.create_index('idx_should_auto_moderate', 'ai_moderation_results', ['should_auto_moderate'])
    op.create_index('idx_ai_content_id', 'ai_moderation_results', ['content_id'])

    # Create ai_model_training_data table
    op.create_table(
        'ai_model_training_data',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('ai_result_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('ai_toxicity_score', sa.Float(), nullable=False),
        sa.Column('ai_recommended_action', sa.String(50), nullable=False),
        sa.Column('human_label', sa.String(50), nullable=False),
        sa.Column('human_suggested_action', sa.String(50), nullable=True),
        sa.Column('moderator_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('moderator_notes', sa.Text(), nullable=True),
        sa.Column('is_used_for_training', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('disagreement_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['ai_result_id'], ['ai_moderation_results.id'], ),
        sa.ForeignKeyConstraint(['moderator_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_human_label', 'ai_model_training_data', ['human_label'])
    op.create_index('idx_training_created_at', 'ai_model_training_data', ['created_at'])
    op.create_index('idx_ai_result_id', 'ai_model_training_data', ['ai_result_id'])

    # Create community_moderation_votes table
    op.create_table(
        'community_moderation_votes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('report_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('vote_type', sa.String(20), nullable=False),
        sa.Column('reasoning', sa.Text(), nullable=True),
        sa.Column('voter_trust_score', sa.Float(), nullable=False, server_default='0.5'),
        sa.Column('vote_weight', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('is_consensus', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('consensus_threshold_reached', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['report_id'], ['reports.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_report_user_vote', 'community_moderation_votes', ['report_id', 'user_id'])
    op.create_index('idx_vote_type', 'community_moderation_votes', ['vote_type'])
    op.create_index('idx_vote_created_at', 'community_moderation_votes', ['created_at'])
    op.create_index('idx_report_id_vote', 'community_moderation_votes', ['report_id'])


def downgrade() -> None:
    op.drop_index('idx_report_id_vote', table_name='community_moderation_votes')
    op.drop_index('idx_vote_created_at', table_name='community_moderation_votes')
    op.drop_index('idx_vote_type', table_name='community_moderation_votes')
    op.drop_index('idx_report_user_vote', table_name='community_moderation_votes')
    op.drop_table('community_moderation_votes')

    op.drop_index('idx_ai_result_id', table_name='ai_model_training_data')
    op.drop_index('idx_training_created_at', table_name='ai_model_training_data')
    op.drop_index('idx_human_label', table_name='ai_model_training_data')
    op.drop_table('ai_model_training_data')

    op.drop_index('idx_should_auto_moderate', table_name='ai_moderation_results')
    op.drop_index('idx_ai_created_at', table_name='ai_moderation_results')
    op.drop_index('idx_content_type_risk', table_name='ai_moderation_results')
    op.drop_index('idx_ai_content_id', table_name='ai_moderation_results')
    op.drop_table('ai_moderation_results')
