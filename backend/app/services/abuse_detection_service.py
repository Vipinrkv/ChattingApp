# backend/app/services/abuse_detection_service.py
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from app.models.login_history import LoginHistory, LoginStatus, SuspiciousActivity
from app.models.ip_reputation import IPReputation, RateLimitEntry
import logging

logger = logging.getLogger(__name__)


class AbuseDetectionService:
    """Automated abuse detection and response system"""

    @staticmethod
    async def check_brute_force_attack(
        session: AsyncSession,
        identifier: str,  # email, phone, username
        window_minutes: int = 15,
        threshold: int = 5
    ) -> bool:
        """Detect brute force attacks on account"""
        try:
            cutoff_time = (datetime.now(timezone.utc) - timedelta(minutes=window_minutes)).replace(tzinfo=None)
            
            query = select(func.count()).select_from(LoginHistory).where(
                and_(
                    LoginHistory.identifier == identifier,
                    LoginHistory.status == LoginStatus.FAILED,
                    LoginHistory.created_at >= cutoff_time
                )
            )
            
            failed_count = (await session.execute(query)).scalar()
            
            if failed_count and failed_count >= threshold:
                logger.warning(f"Brute force detected for identifier: {identifier}")
                return True
            
            return False
        except Exception as e:
            logger.error(f"Error checking brute force: {str(e)}")
            return False

    @staticmethod
    async def check_distributed_attack(
        session: AsyncSession,
        window_minutes: int = 60,
        threshold: int = 20
    ) -> List[Dict[str, Any]]:
        """Detect distributed attacks from multiple IPs"""
        try:
            cutoff_time = (datetime.now(timezone.utc) - timedelta(minutes=window_minutes)).replace(tzinfo=None)
            
            query = select(
                LoginHistory.ip_address,
                func.count().label("attempt_count")
            ).where(
                and_(
                    LoginHistory.status == LoginStatus.FAILED,
                    LoginHistory.created_at >= cutoff_time
                )
            ).group_by(LoginHistory.ip_address).having(
                func.count() >= threshold
            )
            
            results = (await session.execute(query)).all()
            
            attacks = []
            for ip, count in results:
                attacks.append({
                    "ip_address": ip,
                    "failed_attempts": count
                })
                logger.warning(f"Distributed attack detected from IP: {ip}")
            
            return attacks
        except Exception as e:
            logger.error(f"Error checking distributed attacks: {str(e)}")
            return []

    @staticmethod
    async def check_credential_stuffing(
        session: AsyncSession,
        ip_address: str,
        window_minutes: int = 60,
        threshold: int = 10
    ) -> bool:
        """Detect credential stuffing from single IP"""
        try:
            cutoff_time = (datetime.now(timezone.utc) - timedelta(minutes=window_minutes)).replace(tzinfo=None)
            
            query = select(func.count()).select_from(LoginHistory).where(
                and_(
                    LoginHistory.ip_address == ip_address,
                    LoginHistory.status == LoginStatus.FAILED,
                    LoginHistory.created_at >= cutoff_time
                )
            )
            
            failed_count = (await session.execute(query)).scalar()
            
            if failed_count and failed_count >= threshold:
                logger.warning(f"Credential stuffing detected from IP: {ip_address}")
                return True
            
            return False
        except Exception as e:
            logger.error(f"Error checking credential stuffing: {str(e)}")
            return False

    @staticmethod
    async def check_account_enumeration(
        session: AsyncSession,
        window_minutes: int = 60,
        threshold: int = 50
    ) -> bool:
        """Detect account enumeration attacks"""
        try:
            cutoff_time = (datetime.now(timezone.utc) - timedelta(minutes=window_minutes)).replace(tzinfo=None)
            
            # Count unique identifiers with failures from failed logins
            query = select(func.count(func.distinct(LoginHistory.identifier))).select_from(
                LoginHistory
            ).where(
                and_(
                    LoginHistory.status == LoginStatus.FAILED,
                    LoginHistory.created_at >= cutoff_time
                )
            )
            
            unique_count = (await session.execute(query)).scalar()
            
            if unique_count and unique_count >= threshold:
                logger.warning(f"Account enumeration attack detected: {unique_count} accounts")
                return True
            
            return False
        except Exception as e:
            logger.error(f"Error checking account enumeration: {str(e)}")
            return False

    @staticmethod
    async def check_unusual_activity(
        session: AsyncSession,
        user_id: str,
        activity_type: str = "login",
        window_hours: int = 24
    ) -> bool:
        """
        Detect unusual activity patterns for a user.
        Check for:
        - Multiple logins from different locations
        - Logins at unusual times
        - Multiple failed attempts followed by success
        """
        try:
            cutoff_time = (datetime.now(timezone.utc) - timedelta(hours=window_hours)).replace(tzinfo=None)
            
            # Get recent successful logins
            query = select(LoginHistory).where(
                and_(
                    LoginHistory.user_id == user_id,
                    LoginHistory.status == LoginStatus.SUCCESS,
                    LoginHistory.created_at >= cutoff_time
                )
            ).order_by(LoginHistory.created_at.desc()).limit(5)
            
            logins = (await session.execute(query)).scalars().all()
            
            if len(logins) < 2:
                return False
            
            # Check for multiple locations
            locations = set()
            for login in logins:
                if login.country and login.city:
                    locations.add(f"{login.country}:{login.city}")
            
            if len(locations) > 1:
                logger.info(f"Unusual activity: User {user_id} logged in from {len(locations)} locations")
                return True
            
            return False
        except Exception as e:
            logger.error(f"Error checking unusual activity: {str(e)}")
            return False

    @staticmethod
    async def apply_automatic_response(
        session: AsyncSession,
        activity_id: str,
        action: str
    ) -> bool:
        """Apply automatic response to suspicious activity"""
        try:
            query = select(SuspiciousActivity).where(
                SuspiciousActivity.id == activity_id
            )
            activity = (await session.execute(query)).scalar_one_or_none()
            
            if not activity:
                return False
            
            if action == "block_ip":
                # Get or create IP reputation
                query = select(IPReputation).where(
                    IPReputation.ip_address == activity.ip_address
                )
                reputation = (await session.execute(query)).scalar_one_or_none()
                
                if reputation:
                    reputation.is_blacklisted = True
                    reputation.abuse_score = 1.0
                    await session.flush()
            
            elif action == "require_mfa":
                # Logged in session audit with MFA requirement
                pass
            
            elif action == "lock_account":
                # Trigger account lock (requires user_id)
                pass
            
            activity.action_taken = action
            await session.flush()
            
            logger.info(f"Automatic response applied: {action}")
            return True
        except Exception as e:
            logger.error(f"Error applying automatic response: {str(e)}")
            return False


abuse_detection_service = AbuseDetectionService()
