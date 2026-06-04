"""AI Moderation Service - Advanced content safety analysis with external API integration."""
import re
import logging
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.models.ai_moderation import AIModerationResult
from app.models.moderation_action import ModerationAction
from app.models.user import User
from app.schemas.ai_moderation_schema import AIAnalysisResult

logger = logging.getLogger(__name__)


class AIModerationService:
    """Comprehensive AI-driven content moderation using external APIs and ML models."""

    # Configuration thresholds
    TOXICITY_THRESHOLD = 0.6
    SEVERE_TOXICITY_THRESHOLD = 0.7
    SPAM_CONFIDENCE_THRESHOLD = 0.65
    NSFW_CONFIDENCE_THRESHOLD = 0.6

    # Spam patterns
    SPAM_PATTERNS = [
        r"\b(?:follow|like|click|subscribe|visit|buy|win|free|claim|download)\b.*(?:link|url|now|today|asap)",
        r"(?:http|https|www\.)\S+.*(?:casino|poker|dating|weight|pills|viagra)",
        r"\b(?:\d{10,}|contact\s*me|dm\s*me|check\s*this)\b.*(?:@|telegram|whatsapp)",
        r"(?:GET|EARN|MAKE).*(?:\$|₹|€).*(?:FAST|QUICK|EASY|NOW)",
    ]

    # Phishing patterns
    PHISHING_PATTERNS = [
        r"verify\s+(?:your|account|email|identity|payment)",
        r"confirm\s+(?:credentials|password|email|account)",
        r"(?:click|tap)\s+(?:here|link)\s+(?:immediately|urgently|now)",
        r"suspend|locked|urgent action required|limited time",
    ]

    # Harmful link patterns
    HARMFUL_DOMAINS = [
        r"(?:bit\.ly|tinyurl|short\.link)",  # URL shorteners (often hide malicious links)
        r"(?:casino|poker|bet|gambling|adult|xxx|pornography)",
        r"(?:fake.*?(?:id|document|credential)|forge)",
        r"(?:malware|ransomware|trojan|botnet|ddos)",
    ]

    @staticmethod
    async def analyze_content(
        session: AsyncSession,
        content_id: str,
        content_type: str,  # "message", "post", "comment"
        content_text: str,
        media_urls: Optional[list[str]] = None,
    ) -> AIAnalysisResult:
        """
        Comprehensive AI analysis of content for safety, toxicity, spam, and other risks.
        Returns AIAnalysisResult with scores, flags, and recommendations.
        """
        try:
            # Run all analyses in parallel where possible
            toxicity_result = await AIModerationService._analyze_toxicity(content_text)
            spam_result = AIModerationService._analyze_spam(content_text)
            link_result = AIModerationService._analyze_links(content_text)
            phishing_result = AIModerationService._analyze_phishing(content_text)
            nsfw_result = await AIModerationService._analyze_nsfw(content_text, media_urls or [])

            # Determine overall risk level and action
            overall_risk_level, should_auto_moderate, recommended_action = \
                AIModerationService._calculate_overall_risk(
                    toxicity_result,
                    spam_result,
                    link_result,
                    phishing_result,
                    nsfw_result,
                )

            # Compile detected issues
            detected_issues = {
                "toxicity_details": toxicity_result.get("details", {}),
                "spam_patterns": spam_result.get("patterns_found", []),
                "harmful_links": link_result.get("links_found", []),
                "phishing_indicators": phishing_result.get("indicators", []),
                "nsfw_details": nsfw_result.get("details", {}),
            }

            # Create result object
            result = AIAnalysisResult(
                content_id=content_id,
                content_type=content_type,
                toxicity_score=toxicity_result.get("toxicity_score", 0.0),
                severe_toxicity_score=toxicity_result.get("severe_toxicity_score", 0.0),
                identity_attack_score=toxicity_result.get("identity_attack_score", 0.0),
                insult_score=toxicity_result.get("insult_score", 0.0),
                profanity_score=toxicity_result.get("profanity_score", 0.0),
                threat_score=toxicity_result.get("threat_score", 0.0),
                is_spam=spam_result.get("is_spam", False),
                is_nsfw=nsfw_result.get("is_nsfw", False),
                has_harmful_links=link_result.get("has_harmful_links", False),
                is_phishing=phishing_result.get("is_phishing", False),
                overall_risk_level=overall_risk_level,
                should_auto_moderate=should_auto_moderate,
                recommended_action=recommended_action,
                confidence_score=max(
                    toxicity_result.get("confidence", 0.0),
                    spam_result.get("confidence", 0.0),
                    nsfw_result.get("confidence", 0.0),
                ),
                detected_issues=detected_issues,
            )

            # Store result in database
            result_data = result.dict()
            result_data.pop("content_id", None)
            result_data.pop("content_type", None)

            db_result = AIModerationResult(
                content_id=content_id,
                content_type=content_type,
                content_text=content_text,
                **result_data
            )
            session.add(db_result)
            await session.flush()

            return result

        except Exception as exc:
            logger.exception("Error in AI content analysis: %s", exc)
            # Return neutral result on error
            return AIAnalysisResult(
                content_id=content_id,
                content_type=content_type,
                toxicity_score=0.0,
                overall_risk_level="low",
                should_auto_moderate=False,
                recommended_action="none",
            )

    @staticmethod
    async def _analyze_toxicity(content_text: str) -> dict:
        """Analyze toxicity using Google Perspective API if configured, fallback to heuristics."""
        if not settings.PERSPECTIVE_API_KEY:
            return AIModerationService._analyze_toxicity_heuristic(content_text)

        try:
            import httpx
            async with httpx.AsyncClient(timeout=10) as client:
                url = "https://commentanalyzer.googleapis.com/v1/comments:analyzeComment"
                params = {
                    "key": settings.PERSPECTIVE_API_KEY,
                }
                payload = {
                    "comment": {"text": content_text},
                    "requestedAttributes": {
                        "TOXICITY": {},
                        "SEVERE_TOXICITY": {},
                        "IDENTITY_ATTACK": {},
                        "INSULT": {},
                        "PROFANITY": {},
                        "THREAT": {},
                    },
                    "languages": ["en"],
                }

                resp = await client.post(url, params=params, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    scores = data.get("attributeScores", {})
                    return {
                        "toxicity_score": scores.get("TOXICITY", {}).get("summaryScore", {}).get("value", 0.0),
                        "severe_toxicity_score": scores.get("SEVERE_TOXICITY", {}).get("summaryScore", {}).get("value", 0.0),
                        "identity_attack_score": scores.get("IDENTITY_ATTACK", {}).get("summaryScore", {}).get("value", 0.0),
                        "insult_score": scores.get("INSULT", {}).get("summaryScore", {}).get("value", 0.0),
                        "profanity_score": scores.get("PROFANITY", {}).get("summaryScore", {}).get("value", 0.0),
                        "threat_score": scores.get("THREAT", {}).get("summaryScore", {}).get("value", 0.0),
                        "confidence": 0.95,
                        "details": {"source": "perspective_api"},
                    }
        except Exception as exc:
            logger.warning("Perspective API error: %s", exc)

        return AIModerationService._analyze_toxicity_heuristic(content_text)

    @staticmethod
    def _analyze_toxicity_heuristic(content_text: str) -> dict:
        """Heuristic-based toxicity analysis as fallback."""
        text_lower = content_text.lower()

        # Toxicity keyword patterns
        severe_toxic_words = r"\b(?:kill|die|suicide|rape|bomb|terrorist|explosion)\b"
        toxic_insults = r"\b(?:idiot|stupid|moron|dumb|retard|loser|scumbag)\b"
        threat_words = r"\b(?:gonna hurt|will kill|going to harm|i'll beat)\b"
        profanity = r"\b(?:damn|hell|crap|damn)\b"

        severe_toxicity = 0.8 if re.search(severe_toxic_words, text_lower) else 0.0
        insult_score = 0.7 if re.search(toxic_insults, text_lower) else 0.0
        threat_score = 0.9 if re.search(threat_words, text_lower) else 0.0
        profanity_score = 0.4 if re.search(profanity, text_lower) else 0.0

        # Overall toxicity
        toxicity_score = max(severe_toxicity * 0.5, insult_score * 0.4, threat_score * 0.8, profanity_score * 0.2)

        return {
            "toxicity_score": min(toxicity_score, 1.0),
            "severe_toxicity_score": min(severe_toxicity, 1.0),
            "identity_attack_score": 0.0,
            "insult_score": min(insult_score, 1.0),
            "profanity_score": min(profanity_score, 1.0),
            "threat_score": min(threat_score, 1.0),
            "confidence": 0.60,
            "details": {"source": "heuristic", "method": "keyword_matching"},
        }

    @staticmethod
    def _analyze_spam(content_text: str) -> dict:
        """Detect spam using pattern matching and heuristics."""
        text_lower = content_text.lower()
        patterns_found = []
        spam_indicators = 0

        for pattern in AIModerationService.SPAM_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                patterns_found.append(pattern)
                spam_indicators += 1

        # Additional spam heuristics
        capitalization_ratio = sum(1 for c in content_text if c.isupper()) / max(len(content_text), 1)
        if capitalization_ratio > 0.3:
            spam_indicators += 0.5

        url_count = len(re.findall(r"(?:http|https|www\.)\S+", content_text))
        if url_count > 2:
            spam_indicators += 1

        mention_count = len(re.findall(r"@\w+", content_text))
        if mention_count > 5:
            spam_indicators += 0.5

        is_spam = spam_indicators >= 1.5
        confidence = min(spam_indicators / 3.0, 1.0)

        return {
            "is_spam": is_spam,
            "patterns_found": patterns_found,
            "spam_score": min(spam_indicators / 3.0, 1.0),
            "confidence": confidence,
        }

    @staticmethod
    def _analyze_links(content_text: str) -> dict:
        """Detect harmful links and URL shorteners."""
        links = re.findall(r"(?:http|https|www\.)\S+", content_text)
        harmful_links = []

        for link in links:
            for pattern in AIModerationService.HARMFUL_DOMAINS:
                if re.search(pattern, link, re.IGNORECASE):
                    harmful_links.append(link)
                    break

        has_harmful_links = len(harmful_links) > 0

        return {
            "has_harmful_links": has_harmful_links,
            "links_found": harmful_links,
            "total_links": len(links),
            "confidence": 0.85 if has_harmful_links else 0.95,
        }

    @staticmethod
    def _analyze_phishing(content_text: str) -> dict:
        """Detect phishing attempts and social engineering."""
        text_lower = content_text.lower()
        indicators = []

        for pattern in AIModerationService.PHISHING_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                indicators.append(pattern)

        is_phishing = len(indicators) >= 2

        return {
            "is_phishing": is_phishing,
            "indicators": indicators,
            "indicator_count": len(indicators),
            "confidence": min(len(indicators) / 3.0, 1.0),
        }

    @staticmethod
    async def _analyze_nsfw(content_text: str, media_urls: list[str]) -> dict:
        """Detect NSFW content in text and media using heuristics."""
        text_lower = content_text.lower()

        # NSFW keyword detection
        nsfw_keywords = r"\b(?:porn|xxx|sex|nude|explicit|adult|sexy|horny|naked)\b"
        has_nsfw_text = bool(re.search(nsfw_keywords, text_lower))

        # Media analysis would require external API like Google Vision API
        # For now, using heuristic detection
        has_nsfw_media = False
        media_flags = []

        # Placeholder for actual media analysis
        for url in media_urls:
            # In production, call Google Vision API or similar
            # is_nsfw_media = await AIModerationService._check_image_nsfw(url)
            pass

        is_nsfw = has_nsfw_text or has_nsfw_media

        return {
            "is_nsfw": is_nsfw,
            "has_nsfw_text": has_nsfw_text,
            "has_nsfw_media": has_nsfw_media,
            "media_flags": media_flags,
            "confidence": 0.75,
            "details": {"method": "keyword_and_media_heuristics"},
        }

    @staticmethod
    def _calculate_overall_risk(
        toxicity: dict,
        spam: dict,
        links: dict,
        phishing: dict,
        nsfw: dict,
    ) -> tuple[str, bool, str]:
        """Calculate overall risk level and recommended action."""

        risk_score = 0.0
        risk_factors = []

        # Weight different factors
        if toxicity.get("toxicity_score", 0.0) > AIModerationService.TOXICITY_THRESHOLD:
            risk_score += 0.3
            risk_factors.append("toxicity")

        if toxicity.get("severe_toxicity_score", 0.0) > AIModerationService.SEVERE_TOXICITY_THRESHOLD:
            risk_score += 0.4
            risk_factors.append("severe_toxicity")

        if spam.get("is_spam", False):
            risk_score += 0.25
            risk_factors.append("spam")

        if phishing.get("is_phishing", False):
            risk_score += 0.35
            risk_factors.append("phishing")

        if links.get("has_harmful_links", False):
            risk_score += 0.3
            risk_factors.append("harmful_links")

        if nsfw.get("is_nsfw", False):
            risk_score += 0.2
            risk_factors.append("nsfw")

        # Determine risk level
        if risk_score >= 0.7:
            overall_risk_level = "critical"
            recommended_action = "delete"
            should_auto_moderate = True
        elif risk_score >= 0.5:
            overall_risk_level = "high"
            recommended_action = "shadow_ban"
            should_auto_moderate = True
        elif risk_score >= 0.3:
            overall_risk_level = "medium"
            recommended_action = "flag"
            should_auto_moderate = False
        else:
            overall_risk_level = "low"
            recommended_action = "none"
            should_auto_moderate = False

        # Adjust for specific conditions
        if phishing.get("is_phishing", False) or links.get("has_harmful_links", False):
            recommended_action = "delete"
            should_auto_moderate = True

        if toxicity.get("severe_toxicity_score", 0.0) > AIModerationService.SEVERE_TOXICITY_THRESHOLD:
            recommended_action = "suspend"
            should_auto_moderate = True

        return overall_risk_level, should_auto_moderate, recommended_action

    @staticmethod
    async def apply_auto_moderation(
        session: AsyncSession,
        user_id: str,
        ai_result: AIModerationResult,
        content_ids: Optional[list[str]] = None,
    ) -> Optional[ModerationAction]:
        """Apply automatic moderation action based on AI analysis."""
        if not ai_result.should_auto_moderate:
            return None

        try:
            action_type_mapping = {
                "flag": "flag",
                "shadow_ban": "shadow_ban",
                "suspend": "suspend",
                "delete": "delete_content",
            }

            action_type = action_type_mapping.get(ai_result.recommended_action, "flag")

            # Create moderation action
            user = await session.get(User, user_id)
            if user:
                if action_type == "shadow_ban":
                    user.is_shadow_banned = True
                elif action_type == "suspend":
                    user.is_suspended = True
                    user.suspended_until = datetime.utcnow() + timedelta(hours=24)

            action = ModerationAction(
                moderator_id=None,
                target_type="user",
                target_id=user_id,
                action_type=action_type,
                reason=f"AI auto-moderation: {ai_result.overall_risk_level} risk - {','.join(ai_result.detected_issues.keys())}",
                action_metadata={
                    "initiated_by": "ai_auto",
                    "content_ids": content_ids or [],
                    "confidence": ai_result.confidence_score,
                    "risk_level": ai_result.overall_risk_level,
                },
                created_at=datetime.utcnow(),
            )

            session.add(action)
            await session.flush()
            logger.info(f"Applied AI auto-moderation: {action_type} for user {user_id}")
            return action

        except Exception as exc:
            logger.exception("Error applying auto-moderation: %s", exc)
            return None
