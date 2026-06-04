"""AI Moderation models for tracking AI-driven content safety analysis."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Boolean, JSON, DateTime, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import UUID
from app.database.connection import Base


class AIModerationResult(Base):
    """Stores AI moderation analysis results for content."""
    __tablename__ = "ai_moderation_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_id = Column(String(255), nullable=False, index=True)
    content_type = Column(String(50), nullable=False)  # "message", "post", "comment"
    content_text = Column(Text, nullable=False)

    # Toxicity scores (0.0 - 1.0)
    toxicity_score = Column(Float, nullable=False, default=0.0)
    severe_toxicity_score = Column(Float, nullable=False, default=0.0)
    identity_attack_score = Column(Float, nullable=False, default=0.0)
    insult_score = Column(Float, nullable=False, default=0.0)
    profanity_score = Column(Float, nullable=False, default=0.0)
    threat_score = Column(Float, nullable=False, default=0.0)

    # Detection flags
    is_spam = Column(Boolean, nullable=False, default=False)
    is_nsfw = Column(Boolean, nullable=False, default=False)
    has_harmful_links = Column(Boolean, nullable=False, default=False)
    is_phishing = Column(Boolean, nullable=False, default=False)

    # Overall risk assessment
    overall_risk_level = Column(String(20), nullable=False, default="low")  # low, medium, high, critical
    should_auto_moderate = Column(Boolean, nullable=False, default=False)

    # AI recommendations
    recommended_action = Column(String(50), nullable=False, default="none")  # none, flag, shadow_ban, suspend, delete
    confidence_score = Column(Float, nullable=False, default=0.0)

    # Analysis details
    detected_issues = Column(JSON, nullable=False, default=dict)  # {"spam_patterns": [...], "toxic_phrases": [...]}
    analysis_metadata = Column(JSON, nullable=False, default=dict)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_content_type_risk", "content_type", "overall_risk_level"),
        Index("idx_created_at", "created_at"),
        Index("idx_should_auto_moderate", "should_auto_moderate"),
    )


class AIModelTrainingData(Base):
    """Tracks training data for continuous AI model improvement."""
    __tablename__ = "ai_model_training_data"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ai_result_id = Column(UUID(as_uuid=True), ForeignKey("ai_moderation_results.id"), nullable=True, index=True)

    # Original AI prediction
    ai_toxicity_score = Column(Float, nullable=False)
    ai_recommended_action = Column(String(50), nullable=False)

    # Human moderator feedback
    human_label = Column(String(50), nullable=False)  # "correct", "false_positive", "false_negative"
    human_suggested_action = Column(String(50), nullable=True)
    moderator_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    moderator_notes = Column(Text, nullable=True)

    # Quality metrics
    is_used_for_training = Column(Boolean, nullable=False, default=False)
    disagreement_score = Column(Float, nullable=False, default=0.0)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_human_label", "human_label"),
        Index("idx_created_at", "created_at"),
    )


class CommunityModerationVote(Base):
    """Community-based moderation voting system."""
    __tablename__ = "community_moderation_votes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id = Column(UUID(as_uuid=True), ForeignKey("reports.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    # Voting
    vote_type = Column(String(20), nullable=False)  # "upheld", "overturned", "abstain"
    reasoning = Column(Text, nullable=True)

    # Reputation
    voter_trust_score = Column(Float, nullable=False, default=0.5)  # 0.0 - 1.0
    vote_weight = Column(Float, nullable=False, default=1.0)  # Weighted by voter reputation

    # Community consensus
    is_consensus = Column(Boolean, nullable=False, default=False)
    consensus_threshold_reached = Column(Boolean, nullable=False, default=False)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_report_user", "report_id", "user_id"),
        Index("idx_vote_type", "vote_type"),
        Index("idx_created_at", "created_at"),
    )
