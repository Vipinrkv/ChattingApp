# backend/app/services/mfa_service.py
import pyotp
import qrcode
import io
import base64
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import secrets
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.models.mfa import MFASetup, MFAMethod
from app.core.security import security_service
import logging

logger = logging.getLogger(__name__)


class MFAService:
    """Multi-Factor Authentication service"""

    @staticmethod
    async def create_totp_setup(
        session: AsyncSession, 
        user_id: str, 
        issuer: str = "ChattingApp"
    ) -> Dict[str, Any]:
        """Create TOTP setup with QR code"""
        try:
            # Generate secret
            secret = pyotp.random_base32()
            
            # Create TOTP provisioning URI
            totp = pyotp.TOTP(secret)
            provisioning_uri = totp.provisioning_uri(
                name=f"user_{user_id}",
                issuer_name=issuer
            )
            
            # Generate QR code
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(provisioning_uri)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            qr_code_b64 = base64.b64encode(buffer.getvalue()).decode()
            
            # Generate backup codes
            backup_codes = [secrets.token_hex(4) for _ in range(10)]
            
            # Store setup (not verified yet)
            encrypted_secret = security_service.encrypt_value(secret)
            encrypted_backup = security_service.encrypt_value("|".join(backup_codes))
            
            mfa_setup = MFASetup(
                user_id=user_id,
                method=MFAMethod.TOTP,
                secret=encrypted_secret,
                backup_codes=encrypted_backup,
                is_verified=False
            )
            session.add(mfa_setup)
            await session.flush()
            
            logger.info(f"TOTP setup created for user {user_id}")
            
            return {
                "setup_id": str(mfa_setup.id),
                "secret": secret,  # Return unencrypted secret for display
                "qr_code": f"data:image/png;base64,{qr_code_b64}",
                "backup_codes": backup_codes,
                "method": MFAMethod.TOTP
            }
        except Exception as e:
            logger.error(f"Error creating TOTP setup: {str(e)}")
            raise

    @staticmethod
    async def verify_totp(
        session: AsyncSession,
        user_id: str,
        setup_id: str,
        token: str
    ) -> bool:
        """Verify TOTP token"""
        try:
            query = select(MFASetup).where(
                and_(
                    MFASetup.id == setup_id,
                    MFASetup.user_id == user_id,
                    MFASetup.method == MFAMethod.TOTP,
                    MFASetup.is_verified == False
                )
            )
            setup = (await session.execute(query)).scalar_one_or_none()
            
            if not setup or not setup.secret:
                return False
            
            decrypted_secret = security_service.decrypt_value(setup.secret)
            totp = pyotp.TOTP(decrypted_secret)
            
            # Allow 30-second window
            if totp.verify(token, valid_window=1):
                setup.is_verified = True
                setup.verified_at = datetime.utcnow()
                setup.is_active = True
                await session.flush()
                
                logger.info(f"TOTP verified for user {user_id}")
                return True
            
            return False
        except Exception as e:
            logger.error(f"Error verifying TOTP: {str(e)}")
            return False

    @staticmethod
    async def verify_backup_code(
        session: AsyncSession,
        user_id: str,
        code: str
    ) -> bool:
        """Verify and consume a backup code"""
        try:
            query = select(MFASetup).where(
                and_(
                    MFASetup.user_id == user_id,
                    MFASetup.is_active == True,
                    MFASetup.is_verified == True
                )
            )
            setup = (await session.execute(query)).scalar_one_or_none()
            
            if not setup or not setup.backup_codes:
                return False
            
            decrypted_codes = security_service.decrypt_value(setup.backup_codes)
            codes = decrypted_codes.split("|")
            
            if code in codes:
                # Remove used code
                codes.remove(code)
                setup.backup_codes = security_service.encrypt_value("|".join(codes))
                await session.flush()
                
                logger.info(f"Backup code used for user {user_id}")
                return True
            
            return False
        except Exception as e:
            logger.error(f"Error verifying backup code: {str(e)}")
            return False

    @staticmethod
    async def disable_mfa(
        session: AsyncSession,
        user_id: str,
        method: MFAMethod
    ) -> bool:
        """Disable MFA for user"""
        try:
            query = select(MFASetup).where(
                and_(
                    MFASetup.user_id == user_id,
                    MFASetup.method == method,
                    MFASetup.is_active == True
                )
            )
            setup = (await session.execute(query)).scalar_one_or_none()
            
            if setup:
                setup.is_active = False
                await session.flush()
                logger.info(f"MFA disabled for user {user_id}")
                return True
            
            return False
        except Exception as e:
            logger.error(f"Error disabling MFA: {str(e)}")
            return False

    @staticmethod
    async def get_active_mfa_methods(
        session: AsyncSession,
        user_id: str
    ) -> List[MFAMethod]:
        """Get all active MFA methods for user"""
        try:
            query = select(MFASetup).where(
                and_(
                    MFASetup.user_id == user_id,
                    MFASetup.is_verified == True,
                    MFASetup.is_active == True
                )
            )
            setups = (await session.execute(query)).scalars().all()
            return [setup.method for setup in setups]
        except Exception as e:
            logger.error(f"Error getting MFA methods: {str(e)}")
            return []


mfa_service = MFAService()
