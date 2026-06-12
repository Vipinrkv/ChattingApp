# backend/app/services/login_history_service.py
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from app.models.login_history import LoginHistory, LoginStatus, SuspiciousActivity
from app.utils.geo_location import get_location_from_ip
import logging

logger = logging.getLogger(__name__)


class LoginHistoryService:
    """Track and manage login attempts and suspicious activities"""

    @staticmethod
    async def record_login_attempt(
        session: AsyncSession,
        user_id: Optional[str],
        status: LoginStatus,
        method: str,
        identifier: str,
        ip_address: str,
        device_info: Dict[str, Any],
        failure_reason: Optional[str] = None
    ) -> str:
        """Record a login attempt"""
        try:
            # Get geolocation
            geo_info = await get_location_from_ip(ip_address)
            
            # Check if suspicious
            is_suspicious = await LoginHistoryService.is_suspicious_login(
                session, user_id, ip_address, device_info.get("device_id")
            )
            
            login_entry = LoginHistory(
                user_id=user_id,
                status=status,
                method=method,
                identifier=identifier,
                device_id=device_info.get("device_id"),
                device_name=device_info.get("device_name"),
                user_agent=device_info.get("user_agent"),
                browser=device_info.get("browser"),
                os=device_info.get("os"),
                ip_address=ip_address,
                country=geo_info.get("country"),
                city=geo_info.get("city"),
                latitude=geo_info.get("latitude"),
                longitude=geo_info.get("longitude"),
                is_suspicious=is_suspicious,
                is_new_device=device_info.get("is_new_device", False),
                is_new_location=device_info.get("is_new_location", False),
                failure_reason=failure_reason
            )
            
            session.add(login_entry)
            await session.flush()
            
            logger.info(f"Login attempt recorded: user={user_id}, status={status}, ip={ip_address}")
            
            return str(login_entry.id)
        except Exception as e:
            logger.error(f"Error recording login attempt: {str(e)}")
            raise

    @staticmethod
    async def is_suspicious_login(
        session: AsyncSession,
        user_id: Optional[str],
        ip_address: str,
        device_id: Optional[str]
    ) -> bool:
        """Determine if login attempt is suspicious"""
        try:
            if not user_id:
                return False
            
            # Check failed attempts from IP
            query = select(func.count()).select_from(LoginHistory).where(
                and_(
                    LoginHistory.ip_address == ip_address,
                    LoginHistory.status == LoginStatus.FAILED,
                    LoginHistory.created_at > (datetime.now(timezone.utc) - timedelta(hours=1)).replace(tzinfo=None)
                )
            )
            failed_count = (await session.execute(query)).scalar()
            
            if failed_count and failed_count > 5:
                return True
            
            # Check if device is new to user
            if device_id:
                query = select(LoginHistory).where(
                    and_(
                        LoginHistory.user_id == user_id,
                        LoginHistory.device_id == device_id,
                        LoginHistory.status == LoginStatus.SUCCESS
                    )
                ).limit(1)
                
                existing = (await session.execute(query)).scalar_one_or_none()
                if not existing:
                    return True  # New device
            
            return False
        except Exception as e:
            logger.error(f"Error checking suspicious login: {str(e)}")
            return False

    @staticmethod
    async def record_suspicious_activity(
        session: AsyncSession,
        activity_type: str,
        severity: str,
        ip_address: str,
        description: str,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        action_taken: Optional[str] = None
    ) -> str:
        """Record suspicious activity"""
        try:
            geo_info = await get_location_from_ip(ip_address)
            
            activity = SuspiciousActivity(
                user_id=user_id,
                activity_type=activity_type,
                severity=severity,
                ip_address=ip_address,
                country=geo_info.get("country"),
                description=description,
                activity_metadata=metadata,
                action_taken=action_taken or "none"
            )
            
            session.add(activity)
            await session.flush()
            
            logger.warning(f"Suspicious activity recorded: type={activity_type}, severity={severity}")
            
            return str(activity.id)
        except Exception as e:
            logger.error(f"Error recording suspicious activity: {str(e)}")
            raise

    @staticmethod
    async def get_recent_logins(
        session: AsyncSession,
        user_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get recent login history for user"""
        try:
            query = select(LoginHistory).where(
                LoginHistory.user_id == user_id
            ).order_by(
                LoginHistory.created_at.desc()
            ).limit(limit)
            
            logins = (await session.execute(query)).scalars().all()
            
            return [
                {
                    "id": str(l.id),
                    "status": l.status.value,
                    "method": l.method,
                    "device_name": l.device_name,
                    "browser": l.browser,
                    "os": l.os,
                    "ip_address": l.ip_address,
                    "country": l.country,
                    "city": l.city,
                    "is_suspicious": l.is_suspicious,
                    "created_at": l.created_at.isoformat()
                }
                for l in logins
            ]
        except Exception as e:
            logger.error(f"Error getting login history: {str(e)}")
            return []


login_history_service = LoginHistoryService()
