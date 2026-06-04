# backend/app/services/security_audit_service.py
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.models.security_audit import SecurityAudit
import logging

logger = logging.getLogger(__name__)


class SecurityAuditService:
    """Security audit logging service"""

    @staticmethod
    async def log_event(
        session: AsyncSession,
        event_type: str,
        action: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Log a security event"""
        try:
            audit = SecurityAudit(
                user_id=user_id,
                event_type=event_type,
                action=action,
                description=description,
                ip_address=ip_address,
                user_agent=user_agent,
                audit_metadata=metadata
            )
            
            session.add(audit)
            await session.flush()
            
            logger.info(
                f"Security audit logged: event_type={event_type}, "
                f"action={action}, user_id={user_id}"
            )
            
            return str(audit.id)
        except Exception as e:
            logger.error(f"Error logging security audit: {str(e)}")
            raise

    @staticmethod
    async def get_user_audit_logs(
        session: AsyncSession,
        user_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get audit logs for a specific user"""
        try:
            query = select(SecurityAudit).where(
                SecurityAudit.user_id == user_id
            ).order_by(
                SecurityAudit.created_at.desc()
            ).limit(limit)
            
            logs = (await session.execute(query)).scalars().all()
            
            return [
                {
                    "id": str(log.id),
                    "event_type": log.event_type,
                    "action": log.action,
                    "description": log.description,
                    "ip_address": log.ip_address,
                    "created_at": log.created_at.isoformat()
                }
                for log in logs
            ]
        except Exception as e:
            logger.error(f"Error getting audit logs: {str(e)}")
            return []


security_audit_service = SecurityAuditService()
