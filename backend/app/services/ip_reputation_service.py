# backend/app/services/ip_reputation_service.py
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.models.ip_reputation import IPReputation, RateLimitEntry
from app.utils.geo_location import get_location_from_ip
import logging

logger = logging.getLogger(__name__)


class IPReputationService:
    """Manage IP reputation and rate limiting"""

    @staticmethod
    async def get_or_create_reputation(
        session: AsyncSession,
        ip_address: str
    ) -> IPReputation:
        """Get or create IP reputation record"""
        try:
            query = select(IPReputation).where(IPReputation.ip_address == ip_address)
            reputation = (await session.execute(query)).scalar_one_or_none()
            
            if not reputation:
                geo_info = await get_location_from_ip(ip_address)
                
                reputation = IPReputation(
                    ip_address=ip_address,
                    country=geo_info.get("country"),
                    city=geo_info.get("city"),
                    latitude=geo_info.get("latitude"),
                    longitude=geo_info.get("longitude"),
                    timezone=geo_info.get("timezone"),
                    isp=geo_info.get("isp"),
                    organization=geo_info.get("organization")
                )
                
                session.add(reputation)
                await session.flush()
            
            return reputation
        except Exception as e:
            logger.error(f"Error getting IP reputation: {str(e)}")
            raise

    @staticmethod
    async def record_failed_login(
        session: AsyncSession,
        ip_address: str
    ) -> None:
        """Record failed login attempt for IP"""
        try:
            reputation = await IPReputationService.get_or_create_reputation(
                session, ip_address
            )
            
            reputation.failed_login_attempts += 1
            
            # Increase abuse score
            if reputation.failed_login_attempts > 10:
                reputation.abuse_score = min(1.0, reputation.abuse_score + 0.1)
                reputation.is_blacklisted = True
            
            await session.flush()
        except Exception as e:
            logger.error(f"Error recording failed login: {str(e)}")

    @staticmethod
    async def record_successful_login(
        session: AsyncSession,
        ip_address: str
    ) -> None:
        """Record successful login for IP"""
        try:
            reputation = await IPReputationService.get_or_create_reputation(
                session, ip_address
            )
            
            reputation.successful_logins += 1
            
            # Improve reputation score
            reputation.reputation_score = min(1.0, reputation.reputation_score + 0.05)
            
            await session.flush()
        except Exception as e:
            logger.error(f"Error recording successful login: {str(e)}")

    @staticmethod
    async def check_rate_limit(
        session: AsyncSession,
        limit_key: str,
        max_attempts: int,
        window_seconds: int
    ) -> bool:
        """Check if rate limit is exceeded"""
        try:
            from datetime import timedelta
            
            query = select(RateLimitEntry).where(
                and_(
                    RateLimitEntry.limit_key == limit_key,
                    RateLimitEntry.expires_at > datetime.now(timezone.utc).replace(tzinfo=None)
                )
            )
            entry = (await session.execute(query)).scalar_one_or_none()
            
            if entry:
                entry.attempt_count += 1
                await session.flush()
                
                return entry.attempt_count <= max_attempts
            
            # Create new entry
            new_entry = RateLimitEntry(
                limit_key=limit_key,
                attempt_count=1,
                max_attempts=max_attempts,
                expires_at=(datetime.now(timezone.utc) + timedelta(seconds=window_seconds)).replace(tzinfo=None)
            )
            session.add(new_entry)
            await session.flush()
            
            return True
        except Exception as e:
            logger.error(f"Error checking rate limit: {str(e)}")
            return True  # Allow on error

    @staticmethod
    async def get_reputation(
        session: AsyncSession,
        ip_address: str
    ) -> Dict[str, Any]:
        """Get IP reputation data"""
        try:
            reputation = await IPReputationService.get_or_create_reputation(
                session, ip_address
            )
            
            return {
                "ip_address": reputation.ip_address,
                "reputation_score": reputation.reputation_score,
                "abuse_score": reputation.abuse_score,
                "is_vpn": reputation.is_vpn,
                "is_proxy": reputation.is_proxy,
                "is_datacenter": reputation.is_datacenter,
                "is_blacklisted": reputation.is_blacklisted,
                "country": reputation.country,
                "city": reputation.city,
                "isp": reputation.isp,
                "organization": reputation.organization
            }
        except Exception as e:
            logger.error(f"Error getting reputation: {str(e)}")
            raise


ip_reputation_service = IPReputationService()
