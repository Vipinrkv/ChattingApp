import re
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.redis_cache import redis_cache
from app.core.transaction import run_transaction
from app.models.group import Group
from app.models.group_message import GroupMessage
from app.models.group_post import GroupPost
from app.models.message import Message
from app.models.moderation_action import ModerationAction
from app.models.post import Post
from app.models.report import Report
from app.models.report_evidence import ReportEvidence
from app.models.user import User
from app.services.user_service import UserService

logger = logging.getLogger(__name__)


class ModerationError(Exception):
    pass


class ModerationService:
    MESSAGE_RATE_LIMIT = 30
    MESSAGE_RATE_WINDOW_SECONDS = 60
    SUSPICIOUS_CONTENT_PATTERNS = [
        re.compile(pattern, re.IGNORECASE)
        for pattern in [
            r"<\s*script",
            r"javascript:",
            r"data:text/html",
            r"data:image/svg\+xml",
            r"<\s*iframe",
            r"\b(?:rm\s+-rf|sudo|curl\s+\S+\s+\|\s+bash)\b",
            r"\bhttps?://\S+\.(?:exe|bat|cmd|sh)\b",
            r"\bwww\.\S+\.(?:exe|bat|cmd|sh)\b",
        ]
    ]

    @staticmethod
    async def _refresh_user_moderation(session: AsyncSession, user: User) -> None:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        changed = False
        if user.is_suspended and user.suspended_until and user.suspended_until <= now:
            user.is_suspended = False
            user.suspended_until = None
            changed = True
        if user.is_muted and user.muted_until and user.muted_until <= now:
            user.is_muted = False
            user.muted_until = None
            changed = True
        if changed:
            await session.flush()

    @staticmethod
    async def validate_user_can_send(session: AsyncSession, user_id: str) -> User:
        user = await UserService.get_user_by_id(session, user_id)
        if not user or not user.is_active:
            raise ModerationError("Your account cannot send messages at this time")

        await ModerationService._refresh_user_moderation(session, user)

        if user.is_suspended:
            message = "Your account has been suspended"
            if user.suspended_until:
                message = f"Your account is suspended until {user.suspended_until.isoformat()}"
            raise ModerationError(message)

        if user.is_muted:
            message = "You are muted and cannot send messages at this time"
            if user.muted_until:
                message = f"You are muted until {user.muted_until.isoformat()}"
            raise ModerationError(message)

        return user

    @staticmethod
    async def validate_text_content(content: str) -> None:
        if not content or not content.strip():
            raise ModerationError("Message content is required")

        if len(content) > 2000:
            raise ModerationError("Message content is too long")

        for pattern in ModerationService.SUSPICIOUS_CONTENT_PATTERNS:
            if pattern.search(content):
                raise ModerationError("Message content contains unsupported or unsafe text")

    @staticmethod
    async def enforce_message_rate_limit(session: AsyncSession, user_id: str) -> None:
        try:
            user_id_value = UUID(user_id)
        except ValueError:
            user_id_value = user_id

        if redis_cache.enabled:
            try:
                count = await redis_cache.increment(
                    f"moderation:message_rate:{user_id}",
                    ex=ModerationService.MESSAGE_RATE_WINDOW_SECONDS,
                )
            except Exception:
                count = 0
        else:
            cutoff = (datetime.now(timezone.utc) - timedelta(seconds=ModerationService.MESSAGE_RATE_WINDOW_SECONDS)).replace(tzinfo=None)
            result = await session.execute(
                select(func.count()).select_from(Message).where(
                    Message.sender_id == user_id_value,
                    Message.timestamp >= cutoff,
                )
            )
            count = result.scalar_one() or 0

        if count > ModerationService.MESSAGE_RATE_LIMIT:
            raise ModerationError("Too many messages sent. Please slow down.")

    @staticmethod
    async def is_user_shadow_banned(session: AsyncSession, user_id: str) -> bool:
        user = await UserService.get_user_by_id(session, user_id)
        return bool(user and user.is_shadow_banned)

    @staticmethod
    async def filter_shadowbanned_messages(
        session: AsyncSession,
        messages: list[Any],
        viewer_id: str,
        viewer_is_admin: bool = False,
    ) -> list[Any]:
        filtered = []
        sender_ids = []
        for message in messages:
            sender_id = message.sender_id
            if str(sender_id) != str(viewer_id):
                sender_ids.append(sender_id)
            filtered.append(message)

        if not sender_ids or viewer_is_admin:
            return messages

        result = await session.execute(
            select(User.id, User.is_shadow_banned).where(User.id.in_(sender_ids))
        )
        shadow_map = {row[0]: row[1] for row in result.all()}

        filtered = [
            message
            for message in messages
            if str(message.sender_id) == str(viewer_id)
            or not shadow_map.get(str(message.sender_id), False)
        ]
        return filtered

    @staticmethod
    async def create_report(
        session: AsyncSession,
        reporter_id: str,
        target_type: str,
        target_id: str,
        reason: str,
        details: str | None = None,
        evidence: list[dict[str, str]] | None = None,
    ) -> Report:
        target_type = target_type.lower()
        if target_type not in {
            "user",
            "message",
            "post",
            "group_message",
            "group_post",
        }:
            raise ModerationError("Invalid report target type")

        if target_type == "user" and target_id == reporter_id:
            raise ModerationError("You cannot report your own account")

        if target_type == "user":
            target = await session.get(User, target_id)
        elif target_type == "message":
            target = await session.get(Message, target_id)
        elif target_type == "post":
            target = await session.get(Post, target_id)
        elif target_type == "group_message":
            target = await session.get(GroupMessage, target_id)
        else:
            target = await session.get(GroupPost, target_id)

        if target is None:
            raise ModerationError("Report target was not found")

        report = Report(
            reporter_id=reporter_id,
            target_type=target_type,
            target_id=target_id,
            reason=reason,
            details=details,
            status="open",
        )
        session.add(report)
        await session.flush()

        if evidence:
            for item in evidence:
                if not item.get("source_url"):
                    continue
                session.add(
                    ReportEvidence(
                        report_id=report.id,
                        source_url=item["source_url"],
                        description=item.get("description"),
                    )
                )

        await session.commit()
        await session.refresh(report)
        return report

    @staticmethod
    async def get_report(session: AsyncSession, report_id: str) -> Report | None:
        return await session.get(Report, report_id)

    @staticmethod
    async def list_reports(
        session: AsyncSession,
        status: str | None = None,
        target_type: str | None = None,
        reporter_id: str | None = None,
        limit: int = 50,
    ) -> list[Report]:
        query = select(Report)
        if status:
            query = query.where(Report.status == status)
        if target_type:
            query = query.where(Report.target_type == target_type)
        if reporter_id:
            query = query.where(Report.reporter_id == reporter_id)
        query = query.order_by(Report.created_at.desc()).limit(limit)
        result = await session.execute(query)
        return result.scalars().all()

    @staticmethod
    async def apply_action(
        session: AsyncSession,
        moderator_id: str,
        report_id: str,
        action_type: str,
        reason: str | None = None,
        duration_minutes: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ModerationAction:
        report = await session.get(Report, report_id)
        if not report:
            raise ModerationError("Report not found")
        if report.status != "open":
            raise ModerationError("Report is already resolved")

        if action_type not in {
            "warning",
            "mute",
            "temporary_suspension",
            "permanent_ban",
            "shadow_ban",
            "unmute",
            "lift_suspension",
            "content_removal",
        }:
            raise ModerationError("Unsupported moderation action")

        target_type = report.target_type
        target_id = report.target_id
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        if action_type in {"mute", "temporary_suspension", "permanent_ban", "shadow_ban", "unmute", "lift_suspension"}:
            if target_type != "user":
                raise ModerationError("User moderation actions must target a user")
            user = await session.get(User, target_id)
            if not user:
                raise ModerationError("Target user not found")

            if action_type == "mute":
                user.is_muted = True
                user.muted_until = now + timedelta(minutes=duration_minutes) if duration_minutes else None
            elif action_type == "temporary_suspension":
                user.is_suspended = True
                user.suspended_until = now + timedelta(minutes=duration_minutes) if duration_minutes else now + timedelta(hours=24)
            elif action_type == "permanent_ban":
                user.is_suspended = True
                user.suspended_until = None
            elif action_type == "shadow_ban":
                user.is_shadow_banned = True
            elif action_type == "unmute":
                user.is_muted = False
                user.muted_until = None
            elif action_type == "lift_suspension":
                user.is_suspended = False
                user.suspended_until = None

            await session.flush()

        if action_type == "content_removal":
            if target_type == "message":
                target = await session.get(Message, target_id)
            elif target_type == "group_message":
                target = await session.get(GroupMessage, target_id)
            elif target_type == "post":
                target = await session.get(Post, target_id)
            elif target_type == "group_post":
                target = await session.get(GroupPost, target_id)
            else:
                raise ModerationError("Content removal is not supported for this report type")
            if not target:
                raise ModerationError("Target content not found")
            await session.delete(target)
            await session.flush()

        action = ModerationAction(
            moderator_id=moderator_id,
            target_type=target_type,
            target_id=target_id,
            action_type=action_type,
            reason=reason,
            action_metadata=metadata,
        )
        session.add(action)

        report.status = "resolved"
        report.reviewed_by = moderator_id
        report.reviewed_at = now
        report.review_notes = reason
        await session.flush()
        await session.commit()
        await session.refresh(action)
        return action

    @staticmethod
    async def resolve_report(
        session: AsyncSession,
        report_id: str,
        moderator_id: str,
        reason: str | None = None,
        status: str = "resolved",
    ) -> Report:
        report = await session.get(Report, report_id)
        if not report:
            raise ModerationError("Report not found")
        if report.status != "open":
            raise ModerationError("Report is already resolved")

        report.status = status
        report.reviewed_by = moderator_id
        report.reviewed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        report.review_notes = reason
        await session.flush()
        await session.commit()
        await session.refresh(report)
        return report

    @staticmethod
    async def validate_content_with_ai(
        session: AsyncSession,
        content_id: str,
        content_type: str,
        content_text: str,
        media_urls: Optional[list[str]] = None,
    ) -> dict:
        """Validate content using AI moderation."""
        try:
            from app.services.ai_moderation_service import AIModerationService
            
            result = await AIModerationService.analyze_content(
                session,
                content_id,
                content_type,
                content_text,
                media_urls,
            )
            return result.dict()
        except Exception as exc:
            logger.warning("AI content validation failed, using basic validation: %s", exc)
            return {
                "content_id": content_id,
                "toxicity_score": 0.0,
                "overall_risk_level": "low",
                "should_auto_moderate": False,
            }

    @staticmethod
    async def calculate_user_trust_score(session: AsyncSession, user_id: str) -> float:
        """Calculate trust score for community moderation voting."""
        user = await UserService.get_user_by_id(session, user_id)
        if not user:
            return 0.0

        base_score = 0.5
        
        # Account age factor (0 to 0.2 points)
        account_age_days = (datetime.now(timezone.utc).replace(tzinfo=None) - user.created_at).days
        age_bonus = min(account_age_days / 365 * 0.2, 0.2)
        
        # Activity factor (0 to 0.15 points)
        activity_bonus = 0.0
        if hasattr(user, 'message_count'):
            activity_bonus = min(user.message_count / 1000 * 0.15, 0.15)
        
        # Report accuracy (0 to 0.15 points - based on previous moderation participation)
        accuracy_bonus = 0.0
        try:
            from app.models.ai_moderation import CommunityModerationVote
            result = await session.execute(
                select(func.count(CommunityModerationVote.id)).where(
                    CommunityModerationVote.user_id == UUID(user_id)
                )
            )
            vote_count = result.scalar_one() or 0
            if vote_count > 0:
                accuracy_bonus = min(0.15, vote_count / 100 * 0.15)
        except Exception:
            pass
        
        trust_score = min(base_score + age_bonus + activity_bonus + accuracy_bonus, 1.0)
        return trust_score

    @staticmethod
    async def apply_ai_auto_moderation(
        session: AsyncSession,
        user_id: str,
        content_id: str,
        ai_analysis: dict,
    ) -> Optional[ModerationAction]:
        """Apply AI-recommended moderation action if appropriate."""
        try:
            if not ai_analysis.get("should_auto_moderate"):
                return None

            from app.services.ai_moderation_service import AIModerationService
            from app.models.ai_moderation import AIModerationResult
            
            # Get AI result
            result = await session.execute(
                select(AIModerationResult).where(
                    AIModerationResult.content_id == content_id
                )
            )
            ai_result = result.scalars().first()
            
            if not ai_result:
                return None

            return await AIModerationService.apply_auto_moderation(
                session,
                user_id,
                ai_result,
                content_ids=[content_id],
            )
        except Exception as exc:
            logger.exception("Error applying AI auto-moderation: %s", exc)
            return None

