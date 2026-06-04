"""Pydantic schemas for AI moderation analysis and results."""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class AIAnalysisResult(BaseModel):
    """Result of AI content analysis."""
    content_id: str
    content_type: str  # "message", "post", "comment"
    
    # Toxicity scores (0.0 - 1.0)
    toxicity_score: float = Field(default=0.0, ge=0.0, le=1.0)
    severe_toxicity_score: float = Field(default=0.0, ge=0.0, le=1.0)
    identity_attack_score: float = Field(default=0.0, ge=0.0, le=1.0)
    insult_score: float = Field(default=0.0, ge=0.0, le=1.0)
    profanity_score: float = Field(default=0.0, ge=0.0, le=1.0)
    threat_score: float = Field(default=0.0, ge=0.0, le=1.0)
    
    # Detection flags
    is_spam: bool = False
    is_nsfw: bool = False
    has_harmful_links: bool = False
    is_phishing: bool = False
    
    # Overall risk assessment
    overall_risk_level: str = "low"  # low, medium, high, critical
    should_auto_moderate: bool = False
    recommended_action: str = "none"  # none, flag, shadow_ban, suspend, delete
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    
    # Analysis details
    detected_issues: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_schema_extra = {
            "example": {
                "content_id": "msg-123",
                "content_type": "message",
                "toxicity_score": 0.85,
                "overall_risk_level": "high",
                "should_auto_moderate": True,
                "recommended_action": "shadow_ban",
                "confidence_score": 0.92,
            }
        }


class CommunityModerationVoteRequest(BaseModel):
    """Community member voting on a report."""
    report_id: str
    vote_type: str  # "upheld", "overturned", "abstain"
    reasoning: Optional[str] = None


class CommunityModerationVoteResponse(BaseModel):
    """Response with vote confirmation and consensus status."""
    vote_id: str
    report_id: str
    vote_type: str
    voter_trust_score: float
    vote_weight: float
    consensus_status: str  # "pending", "reached", "conflicted"
    current_consensus: Optional[str] = None


class SmartReportHandlingRequest(BaseModel):
    """Smart handling of reports with AI insights."""
    report_id: str
    action: str  # "auto_resolve", "flag_for_review", "escalate"
    ai_confidence: float = Field(ge=0.0, le=1.0)
    reason: str


class ModerationActionResponse(BaseModel):
    """Details of a moderation action taken."""
    action_id: str
    target_user_id: str
    action_type: str  # "warning", "mute", "shadow_ban", "suspend", "ban", "delete_content"
    reason: str
    initiated_by: str  # "ai_auto", "ai_human_confirmed", "human_moderator", "community"
    duration_hours: Optional[int] = None
    is_appeal_eligible: bool = True
    created_at: str
    expires_at: Optional[str] = None


class AIModelsHealthCheck(BaseModel):
    """Health status of AI moderation models."""
    perspective_api_available: bool
    vision_api_available: bool
    local_models_status: str  # "ready", "loading", "error"
    last_update: str


class ModeratorInsightsRequest(BaseModel):
    """Request for AI-powered moderator insights."""
    report_id: str
    request_type: str  # "similar_cases", "pattern_analysis", "risk_assessment"


class ModeratorInsightsResponse(BaseModel):
    """AI insights to assist moderators."""
    report_id: str
    similar_cases: List[Dict[str, Any]] = []
    pattern_analysis: Dict[str, Any] = {}
    risk_assessment: Dict[str, Any] = {}
    confidence_scores: Dict[str, float] = {}
    recommendations: List[str] = []
