# backend/app/services/csrf_service.py
import secrets
import hashlib
from typing import Optional
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, delete
from app.models.csrf_token import CSRFToken
import logging

logger = logging.getLogger(__name__)


class CSRFService:
    """CSRF protection using double-submit cookie pattern"""

    @staticmethod
    def generate_token() -> str:
        """Generate a secure CSRF token"""
        return secrets.token_urlsafe(32)

    @staticmethod
    def hash_token(token: str) -> str:
        """Hash token for storage"""
        return hashlib.sha256(token.encode()).hexdigest()

    @staticmethod
    async def create_token(
        session: AsyncSession,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        expires_delta: timedelta = None
    ) -> str:
        """Create a new CSRF token"""
        try:
            if expires_delta is None:
                expires_delta = timedelta(hours=1)
            
            token = CSRFService.generate_token()
            token_hash = CSRFService.hash_token(token)
            
            csrf_token = CSRFToken(
                user_id=user_id,
                token_hash=token_hash,
                session_id=session_id,
                expires_at=(datetime.now(timezone.utc) + expires_delta).replace(tzinfo=None)
            )
            
            session.add(csrf_token)
            await session.flush()
            
            logger.debug(f"CSRF token created for user {user_id}")
            
            return token
        except Exception as e:
            logger.error(f"Error creating CSRF token: {str(e)}")
            raise

    @staticmethod
    async def verify_token(
        session: AsyncSession,
        token: str,
        user_id: Optional[str] = None,
        consume: bool = True,
    ) -> bool:
        """Verify CSRF token"""
        try:
            token_hash = CSRFService.hash_token(token)
            
            query = select(CSRFToken).where(
                and_(
                    CSRFToken.token_hash == token_hash,
                    CSRFToken.is_used == False,
                    CSRFToken.expires_at > datetime.now(timezone.utc).replace(tzinfo=None)
                )
            )
            
            if user_id:
                query = query.where(CSRFToken.user_id == user_id)
            
            csrf_token = (await session.execute(query)).scalar_one_or_none()
            
            if csrf_token:
                if consume:
                    csrf_token.is_used = True
                    csrf_token.used_at = datetime.now(timezone.utc).replace(tzinfo=None)
                await session.flush()
                
                logger.debug("CSRF token verified successfully")
                return True
            
            logger.warning("CSRF token verification failed")
            return False
        except Exception as e:
            logger.error(f"Error verifying CSRF token: {str(e)}")
            return False

    @staticmethod
    async def cleanup_expired_tokens(session: AsyncSession) -> int:
        """Remove expired CSRF tokens"""
        try:
            query = delete(CSRFToken).where(
                CSRFToken.expires_at <= datetime.now(timezone.utc).replace(tzinfo=None)
            )
            result = await session.execute(query)
            await session.flush()
            
            logger.info(f"Cleaned up {result.rowcount} expired CSRF tokens")
            return result.rowcount
        except Exception as e:
            logger.error(f"Error cleaning up CSRF tokens: {str(e)}")
            return 0


csrf_service = CSRFService()
