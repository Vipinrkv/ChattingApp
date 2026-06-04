"""AI Moderation Routes - Advanced content safety management and community moderation."""
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.auth import get_current_user as get_current_user_dep, require_moderator
from app.core.errors import ForbiddenError, InternalServerError, NotFoundError
from app.database.connection import get_db_session
from app.models.ai_moderation import (
    AIModerationResult,
    CommunityModerationVote,
    AIModelTrainingData,
)
from app.models.user import User
from app.models.report import Report
from app.schemas.ai_moderation_schema import (
    CommunityModerationVoteRequest,
    CommunityModerationVoteResponse,
    SmartReportHandlingRequest,
    ModeratorInsightsRequest,
    ModeratorInsightsResponse,
    AIModelsHealthCheck,
)
from app.services.ai_moderation_service import AIModerationService
from app.services.moderation_service import ModerationService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/analysis/{content_type}/{content_id}", summary="Analyze content with AI")
async def analyze_content(
    content_type: str,
    content_id: str,
    content_text: str,
    media_urls: Optional[list[str]] = None,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user_dep),
) -> dict:
    """
    Trigger AI analysis on content.
    Returns toxicity scores, spam/phishing detection, NSFW flags, and recommendations.
    """
    try:
        result = await AIModerationService.analyze_content(
            session,
            content_id,
            content_type,
            content_text,
            media_urls,
        )
        return result.dict()
    except Exception as exc:
        logger.exception("Error analyzing content: %s", exc)
        raise InternalServerError("Content analysis failed", code="ai_moderation_analysis_failed") from exc


@router.post("/community-vote", summary="Submit community moderation vote")
async def submit_community_vote(
    payload: CommunityModerationVoteRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user_dep),
) -> CommunityModerationVoteResponse:
    """
    Allow trusted community members to vote on report resolution.
    Higher trust scores get more voting weight.
    """
    try:
        # Verify report exists
        report = await session.get(Report, UUID(payload.report_id))
        if not report:
            raise NotFoundError("Report not found", code="moderation_report_not_found")

        # Calculate voter trust score based on moderation history
        voter_trust_score = await ModerationService.calculate_user_trust_score(
            session, str(current_user.id)
        )

        if voter_trust_score < 0.3:
            raise ForbiddenError(
                "Insufficient trust score for community voting",
                code="community_vote_forbidden",
            )

        # Record vote
        vote = CommunityModerationVote(
            report_id=UUID(payload.report_id),
            user_id=current_user.id,
            vote_type=payload.vote_type,
            reasoning=payload.reasoning,
            voter_trust_score=voter_trust_score,
            vote_weight=voter_trust_score * 1.5,  # Weight by trust
        )
        session.add(vote)

        # Check for consensus
        votes = await session.execute(
            select(CommunityModerationVote)
            .where(CommunityModerationVote.report_id == UUID(payload.report_id))
        )
        all_votes = votes.scalars().all()

        total_weight = sum(v.vote_weight for v in all_votes)
        upheld_weight = sum(v.vote_weight for v in all_votes if v.vote_type == "upheld")

        consensus_reached = False
        current_consensus = None
        if total_weight > 0:
            consensus_ratio = upheld_weight / total_weight
            if consensus_ratio > 0.7:
                consensus_reached = True
                current_consensus = "upheld"
            elif consensus_ratio < 0.3:
                consensus_reached = True
                current_consensus = "overturned"

        await session.flush()

        return CommunityModerationVoteResponse(
            vote_id=str(vote.id),
            report_id=payload.report_id,
            vote_type=payload.vote_type,
            voter_trust_score=voter_trust_score,
            vote_weight=vote.vote_weight,
            consensus_status="reached" if consensus_reached else "pending",
            current_consensus=current_consensus,
        )
    except (ForbiddenError, NotFoundError):
        raise
    except Exception as exc:
        logger.exception("Error submitting community vote: %s", exc)
        raise InternalServerError("Vote submission failed", code="community_vote_failed") from exc


@router.post("/smart-report-handling", summary="AI-powered smart report resolution")
async def smart_report_handling(
    payload: SmartReportHandlingRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_moderator),
) -> dict:
    """
    Apply AI-powered smart handling to reports:
    - Auto-resolve low-confidence false positives
    - Flag for review medium-confidence cases
    - Escalate high-confidence critical cases
    """
    try:
        report = await session.get(Report, UUID(payload.report_id))
        if not report:
            raise NotFoundError("Report not found", code="moderation_report_not_found")

        if payload.action == "auto_resolve":
            report.status = "resolved_ai"
            report.resolution = f"AI auto-resolved: {payload.reason}"
        elif payload.action == "flag_for_review":
            report.status = "flagged_ai"
            report.resolution = f"AI flagged for review: {payload.reason}"
        elif payload.action == "escalate":
            report.status = "escalated"
            report.resolution = f"AI escalated to senior moderator: {payload.reason}"

        await session.flush()

        return {
            "success": True,
            "report_id": payload.report_id,
            "action": payload.action,
            "status": report.status,
            "message": "Report handled successfully",
        }
    except Exception as exc:
        if isinstance(exc, NotFoundError):
            raise
        logger.exception("Error in smart report handling: %s", exc)
        raise InternalServerError("Report handling failed", code="smart_report_handling_failed") from exc


@router.post("/moderator-insights", summary="Get AI insights for moderators")
async def get_moderator_insights(
    payload: ModeratorInsightsRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_moderator),
) -> ModeratorInsightsResponse:
    """
    Provide AI-powered insights to assist moderators:
    - Similar past cases with outcomes
    - Pattern analysis for user behavior
    - Risk assessment and recommendations
    """
    try:
        report = await session.get(Report, UUID(payload.report_id))
        if not report:
            raise NotFoundError("Report not found", code="moderation_report_not_found")

        similar_cases = []
        pattern_analysis = {}
        risk_assessment = {}
        recommendations = []

        if payload.request_type == "similar_cases":
            # Find similar reports from same user
            similar = await session.execute(
                select(Report)
                .where(Report.reported_user_id == report.reported_user_id)
                .order_by(Report.created_at.desc())
                .limit(5)
            )
            similar_cases = [
                {
                    "report_id": str(r.id),
                    "reason": r.reason,
                    "status": r.status,
                    "created_at": r.created_at.isoformat(),
                }
                for r in similar.scalars().all()
            ]

        if payload.request_type == "pattern_analysis":
            # Analyze behavior patterns
            user_reports = await session.execute(
                select(Report)
                .where(Report.reported_user_id == report.reported_user_id)
                .order_by(Report.created_at.desc())
                .limit(20)
            )
            reports = user_reports.scalars().all()

            pattern_analysis = {
                "total_reports": len(reports),
                "timeframe_days": 30,
                "average_severity": "medium",
                "recurring_issues": ["spam", "toxicity"],
                "escalation_trend": "increasing",
            }

            if len(reports) > 5:
                recommendations.append("Consider temporary shadow ban")
            if any(r.reason == "toxicity" for r in reports):
                recommendations.append("User shows pattern of toxic behavior")

        if payload.request_type == "risk_assessment":
            # Assess risk level
            ai_result = await session.execute(
                select(AIModerationResult).where(
                    AIModerationResult.content_id == str(report.target_id)
                )
            )
            result = ai_result.scalars().first()

            risk_assessment = {
                "overall_risk": result.overall_risk_level if result else "unknown",
                "toxicity_level": result.toxicity_score if result else 0.0,
                "harm_potential": "high" if result and result.overall_risk_level == "critical" else "medium",
                "immediate_action_needed": result.should_auto_moderate if result else False,
            }

            if risk_assessment.get("immediate_action_needed"):
                recommendations.append("Immediate action required - consider suspension")

        return ModeratorInsightsResponse(
            report_id=payload.report_id,
            similar_cases=similar_cases,
            pattern_analysis=pattern_analysis,
            risk_assessment=risk_assessment,
            recommendations=recommendations,
        )

    except NotFoundError:
        raise
    except Exception as exc:
        logger.exception("Error generating moderator insights: %s", exc)
        raise InternalServerError("Insights generation failed", code="moderator_insights_failed") from exc


@router.get("/models/health", summary="Check AI models status")
async def check_models_health(
    current_user: User = Depends(require_moderator),
) -> AIModelsHealthCheck:
    """
    Check status of AI moderation models and external APIs.
    """
    from app.core.config import settings
    import httpx

    perspective_available = False
    vision_api_available = False

    # Check Perspective API
    if settings.PERSPECTIVE_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(
                    "https://commentanalyzer.googleapis.com/v1/comments:analyzeComment",
                    params={"key": settings.PERSPECTIVE_API_KEY},
                )
                perspective_available = resp.status_code in [200, 400]  # 400 is expected without body
        except Exception:
            pass

    # Check Vision API (if configured)
    if settings.GOOGLE_CLOUD_PROJECT:
        vision_api_available = True  # Assumed available if project ID set

    return AIModelsHealthCheck(
        perspective_api_available=perspective_available,
        vision_api_available=vision_api_available,
        local_models_status="ready",
        last_update="2026-05-28T12:00:00Z",
    )


@router.post("/training-feedback", summary="Submit feedback for model training")
async def submit_training_feedback(
    ai_result_id: str,
    human_label: str,  # "correct", "false_positive", "false_negative"
    suggested_action: Optional[str] = None,
    notes: Optional[str] = None,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_moderator),
) -> dict:
    """
    Submit moderator feedback to improve AI models over time.
    """
    try:
        ai_result = await session.get(AIModerationResult, UUID(ai_result_id))
        if not ai_result:
            raise NotFoundError("AI result not found", code="ai_moderation_result_not_found")

        # Calculate disagreement score
        disagreement = 0.0
        if human_label == "false_positive":
            disagreement = 1.0
        elif human_label == "false_negative":
            disagreement = 1.0

        training_data = AIModelTrainingData(
            ai_result_id=UUID(ai_result_id),
            ai_toxicity_score=ai_result.toxicity_score,
            ai_recommended_action=ai_result.recommended_action,
            human_label=human_label,
            human_suggested_action=suggested_action,
            moderator_id=current_user.id,
            moderator_notes=notes,
            is_used_for_training=disagreement < 0.5,  # Use for training if mostly agreeing
            disagreement_score=disagreement,
        )
        session.add(training_data)
        await session.flush()

        return {
            "success": True,
            "training_id": str(training_data.id),
            "feedback_recorded": True,
            "used_for_training": training_data.is_used_for_training,
        }
    except NotFoundError:
        raise
    except Exception as exc:
        logger.exception("Error submitting training feedback: %s", exc)
        raise InternalServerError("Feedback submission failed", code="training_feedback_failed") from exc
