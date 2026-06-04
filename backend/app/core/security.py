# backend/app/core/security.py
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from cryptography.fernet import Fernet
import base64
import hashlib
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class SecurityService:
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using bcrypt"""
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def create_access_token(
        data: dict, expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                hours=settings.JWT_EXPIRATION_HOURS
            )
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(
            to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
        )
        return encoded_jwt

    @staticmethod
    def create_access_token_with_fingerprint(
        data: dict,
        user_agent: str,
        ip_address: str,
        device_id: str,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """Create JWT token with a device fingerprint claim."""
        from app.core.jwt_fingerprint import JWTFingerprint

        to_encode = data.copy()
        to_encode = JWTFingerprint.add_fingerprint_to_token(
            to_encode, user_agent, ip_address, device_id
        )
        return SecurityService.create_access_token(to_encode, expires_delta)

    @staticmethod
    def verify_token(token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(
                token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
            )
            return payload
        except JWTError:
            return None

    @staticmethod
    def verify_token_with_fingerprint(
        token: str,
        user_agent: str,
        ip_address: str,
        device_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Verify JWT and fingerprint claim."""
        try:
            payload = SecurityService.verify_token(token)
            if not payload or "fpr" not in payload:
                return None

            from app.core.jwt_fingerprint import JWTFingerprint

            if not JWTFingerprint.verify_fingerprint(
                payload["fpr"], user_agent, ip_address, device_id
            ):
                return None

            return payload
        except Exception:
            return None

    @staticmethod
    def get_encryption_cipher() -> Fernet:
        """Get Fernet cipher for AES encryption"""
        key = base64.urlsafe_b64encode(
            hashlib.sha256(settings.AES_KEY.encode()).digest()
        )
        return Fernet(key)

    @staticmethod
    def encrypt_message(message: str) -> str:
        """Encrypt message using Fernet"""
        cipher = SecurityService.get_encryption_cipher()
        encrypted = cipher.encrypt(message.encode())
        return encrypted.decode()

    @staticmethod
    def decrypt_message(encrypted_message: str) -> str:
        """Decrypt message using Fernet"""
        cipher = SecurityService.get_encryption_cipher()
        decrypted = cipher.decrypt(encrypted_message.encode())
        return decrypted.decode()

    @staticmethod
    def encrypt_value(value: Optional[str]) -> Optional[str]:
        """Encrypt a value using Fernet"""
        if not value:
            return None
        try:
            return SecurityService.encrypt_message(value)
        except Exception:
            return value

    @staticmethod
    def decrypt_value(value: Optional[str]) -> Optional[str]:
        """Decrypt a value using Fernet"""
        if not value:
            return None
        try:
            return SecurityService.decrypt_message(value)
        except Exception:
            return value


security_service = SecurityService()

# ✅ Wrapper functions for easy import (FIXES YOUR ERROR)

def encrypt_value(value: Optional[str]) -> Optional[str]:
    return security_service.encrypt_value(value)


def decrypt_value(value: Optional[str]) -> Optional[str]:
    return security_service.decrypt_value(value)