# backend/app/services/session_service.py
import uuid
import hashlib
import secrets
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, update, delete
from app.models.session import UserSession, UserDevice, SessionStatus, DeviceType
from app.core.security import security_service
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class SessionService:
    """User session and device management"""

    @staticmethod
    def hash_token(token: str) -> str:
        """Hash token for secure storage"""
        return hashlib.sha256(token.encode()).hexdigest()

    @staticmethod
    async def create_session(
        session: AsyncSession,
        user_id: str,
        device_id: str,
        ip_address: str,
        device_info: Dict[str, Any],
        expires_delta: timedelta = None
    ) -> Dict[str, Any]:
        """Create a new user session"""
        try:
            if isinstance(user_id, str):
                user_id = uuid.UUID(user_id)
            if expires_delta is None:
                expires_delta = timedelta(days=30)  # Default 30-day session
            
            refresh_token = secrets.token_urlsafe(32)
            access_token = secrets.token_urlsafe(32)
            
            user_session = UserSession(
                user_id=user_id,
                device_id=device_id,
                device_name=device_info.get("device_name"),
                device_type=device_info.get("device_type", DeviceType.WEB),
                browser=device_info.get("browser"),
                os=device_info.get("os"),
                user_agent=device_info.get("user_agent"),
                ip_address=ip_address,
                country=device_info.get("country"),
                city=device_info.get("city"),
                latitude=device_info.get("latitude"),
                longitude=device_info.get("longitude"),
                refresh_token_hash=SessionService.hash_token(refresh_token),
                access_token_hash=SessionService.hash_token(access_token),
                status=SessionStatus.ACTIVE,
                expires_at=(datetime.now(timezone.utc) + expires_delta).replace(tzinfo=None)
            )
            
            session.add(user_session)
            await session.flush()
            
            logger.info(f"Session created for user {user_id} from device {device_id}")
            
            return {
                "session_id": str(user_session.id),
                "refresh_token": refresh_token,
                "access_token": access_token,
                "expires_in": int(expires_delta.total_seconds())
            }
        except Exception as e:
            logger.error(f"Error creating session: {str(e)}")
            raise

    @staticmethod
    async def verify_refresh_token(
        session: AsyncSession,
        user_id: str,
        refresh_token: str
    ) -> Optional[Dict[str, Any]]:
        """Verify and validate refresh token"""
        try:
            if isinstance(user_id, str):
                user_id = uuid.UUID(user_id)
            token_hash = SessionService.hash_token(refresh_token)
            
            query = select(UserSession).where(
                and_(
                    UserSession.user_id == user_id,
                    UserSession.refresh_token_hash == token_hash,
                    UserSession.status == SessionStatus.ACTIVE,
                    UserSession.expires_at > datetime.now(timezone.utc).replace(tzinfo=None)
                )
            )
            user_session = (await session.execute(query)).scalar_one_or_none()
            
            if not user_session:
                return None
            
            # Update last activity
            user_session.last_activity_at = datetime.now(timezone.utc).replace(tzinfo=None)
            await session.flush()
            
            return {
                "session_id": str(user_session.id),
                "user_id": str(user_session.user_id),
                "device_id": user_session.device_id,
                "status": user_session.status
            }
        except Exception as e:
            logger.error(f"Error verifying refresh token: {str(e)}")
            return None

    @staticmethod
    async def revoke_session(
        session: AsyncSession,
        session_id: str,
        reason: str = "user_initiated"
    ) -> bool:
        """Revoke a user session"""
        try:
            query = select(UserSession).where(UserSession.id == session_id)
            user_session = (await session.execute(query)).scalar_one_or_none()
            
            if user_session:
                user_session.status = SessionStatus.REVOKED
                user_session.revoked_at = datetime.now(timezone.utc).replace(tzinfo=None)
                user_session.revoke_reason = reason
                await session.flush()
                
                logger.info(f"Session {session_id} revoked: {reason}")
                return True
            
            return False
        except Exception as e:
            logger.error(f"Error revoking session: {str(e)}")
            return False

    @staticmethod
    async def revoke_all_sessions(
        session: AsyncSession,
        user_id: str,
        except_session_id: str = None
    ) -> int:
        """Revoke all sessions for a user"""
        try:
            if isinstance(user_id, str):
                user_id = uuid.UUID(user_id)
            query = select(UserSession).where(
                and_(
                    UserSession.user_id == user_id,
                    UserSession.status == SessionStatus.ACTIVE
                )
            )
            
            if except_session_id:
                query = query.where(UserSession.id != except_session_id)
            
            sessions = (await session.execute(query)).scalars().all()
            
            for user_session in sessions:
                user_session.status = SessionStatus.REVOKED
                user_session.revoked_at = datetime.now(timezone.utc).replace(tzinfo=None)
                user_session.revoke_reason = "security_measure"
            
            await session.flush()
            
            logger.info(f"Revoked {len(sessions)} sessions for user {user_id}")
            return len(sessions)
        except Exception as e:
            logger.error(f"Error revoking all sessions: {str(e)}")
            return 0

    @staticmethod
    async def get_active_sessions(
        session: AsyncSession,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """Get all active sessions for user"""
        try:
            if isinstance(user_id, str):
                user_id = uuid.UUID(user_id)
            query = select(UserSession).where(
                and_(
                    UserSession.user_id == user_id,
                    UserSession.status == SessionStatus.ACTIVE,
                    UserSession.expires_at > datetime.now(timezone.utc).replace(tzinfo=None)
                )
            ).order_by(UserSession.last_activity_at.desc())
            
            sessions = (await session.execute(query)).scalars().all()
            
            return [
                {
                    "session_id": str(s.id),
                    "device_name": s.device_name,
                    "device_type": s.device_type,
                    "browser": s.browser,
                    "os": s.os,
                    "ip_address": s.ip_address,
                    "country": s.country,
                    "city": s.city,
                    "is_trusted": s.is_trusted,
                    "created_at": s.created_at.isoformat(),
                    "last_activity_at": s.last_activity_at.isoformat(),
                    "expires_at": s.expires_at.isoformat()
                }
                for s in sessions
            ]
        except Exception as e:
            logger.error(f"Error getting active sessions: {str(e)}")
            return []

    @staticmethod
    async def trust_device(
        session: AsyncSession,
        device_id: str,
        user_id: str
    ) -> bool:
        """Mark device as trusted"""
        try:
            if isinstance(user_id, str):
                user_id = uuid.UUID(user_id)
            query = select(UserDevice).where(
                and_(
                    UserDevice.device_id == device_id,
                    UserDevice.user_id == user_id
                )
            )
            device = (await session.execute(query)).scalar_one_or_none()
            
            if device:
                device.is_trusted = True
                device.trust_token = secrets.token_urlsafe(32)
                await session.flush()
                
                logger.info(f"Device {device_id} marked as trusted for user {user_id}")
                return True
            
            return False
        except Exception as e:
            logger.error(f"Error trusting device: {str(e)}")
            return False

    @staticmethod
    async def cleanup_expired_sessions(session: AsyncSession) -> int:
        """Remove expired sessions"""
        try:
            query = delete(UserSession).where(
                UserSession.expires_at <= datetime.now(timezone.utc).replace(tzinfo=None)
            )
            result = await session.execute(query)
            await session.flush()
            
            logger.info(f"Cleaned up {result.rowcount} expired sessions")
            return result.rowcount
        except Exception as e:
            logger.error(f"Error cleaning up expired sessions: {str(e)}")
            return 0

    @staticmethod
    async def refresh_session(
        session: AsyncSession,
        user_id: str,
        refresh_token: str,
        ip_address: str,
        user_agent: str,
        device_id: str
    ) -> Optional[Dict[str, Any]]:
        """Verify refresh token, perform rotation (issue new tokens), and update session"""
        try:
            if isinstance(user_id, str):
                user_id = uuid.UUID(user_id)
            token_hash = SessionService.hash_token(refresh_token)
            
            # Look up active session
            query = select(UserSession).where(
                and_(
                    UserSession.user_id == user_id,
                    UserSession.refresh_token_hash == token_hash,
                    UserSession.status == SessionStatus.ACTIVE,
                    UserSession.expires_at > datetime.now(timezone.utc).replace(tzinfo=None)
                )
            )
            user_session = (await session.execute(query)).scalar_one_or_none()
            
            if not user_session:
                logger.warning(f"Suspicious session refresh attempt for user {user_id} - token mismatch or already revoked")
                return None
                
            # Session binding validation: verify that the device ID matches the session
            if user_session.device_id != device_id:
                logger.warning(f"Session binding validation failed: device_id {device_id} does not match session device {user_session.device_id}")
                user_session.status = SessionStatus.REVOKED
                user_session.revoked_at = datetime.now(timezone.utc).replace(tzinfo=None)
                user_session.revoke_reason = "device_id_mismatch"
                await session.flush()
                return None

            # Generate new tokens
            new_refresh_token = secrets.token_urlsafe(32)
            new_access_token = secrets.token_urlsafe(32)
            expires_delta = timedelta(days=30)
            
            # Update the session with new token hashes
            user_session.refresh_token_hash = SessionService.hash_token(new_refresh_token)
            user_session.access_token_hash = SessionService.hash_token(new_access_token)
            user_session.last_activity_at = datetime.now(timezone.utc).replace(tzinfo=None)
            user_session.expires_at = (datetime.now(timezone.utc) + expires_delta).replace(tzinfo=None)
            user_session.ip_address = ip_address
            user_session.user_agent = user_agent
            
            await session.flush()
            
            logger.info(f"Session {user_session.id} refreshed and tokens rotated for user {user_id}")
            
            return {
                "session_id": str(user_session.id),
                "refresh_token": new_refresh_token,
                "access_token": new_access_token,
                "expires_in": int(expires_delta.total_seconds())
            }
        except Exception as e:
            logger.error(f"Error rotating refresh token: {str(e)}")
            return None


session_service = SessionService()
