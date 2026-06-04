# backend/app/core/jwt_fingerprint.py
"""JWT fingerprinting for enhanced security"""
import hashlib
import hmac
from typing import Dict, Any, Optional
from datetime import datetime, timedelta, timezone
import logging

logger = logging.getLogger(__name__)


class JWTFingerprint:
    """JWT Fingerprinting - bind tokens to device/session"""

    @staticmethod
    def create_fingerprint(
        user_agent: str,
        ip_address: str,
        device_id: str
    ) -> str:
        """Create a fingerprint from device characteristics"""
        fingerprint_data = f"{user_agent}|{ip_address}|{device_id}"
        return hashlib.sha256(fingerprint_data.encode()).hexdigest()

    @staticmethod
    def verify_fingerprint(
        stored_fingerprint: str,
        current_user_agent: str,
        current_ip_address: str,
        current_device_id: str,
        tolerance: float = 0.8  # Allow some variance
    ) -> bool:
        """
        Verify fingerprint matches current request.
        
        Allows for some flexibility (e.g., user agent might change slightly)
        """
        try:
            current_fingerprint = JWTFingerprint.create_fingerprint(
                current_user_agent,
                current_ip_address,
                current_device_id
            )
            
            # Strict match is preferred
            if current_fingerprint == stored_fingerprint:
                return True
            
            # For development/testing: allow IP changes (remove this in production)
            # In production, enforce strict matching or use device trust
            
            logger.debug("Fingerprint mismatch detected")
            return False
        except Exception as e:
            logger.error(f"Error verifying fingerprint: {str(e)}")
            return False

    @staticmethod
    def add_fingerprint_to_token(
        token_data: Dict[str, Any],
        user_agent: str,
        ip_address: str,
        device_id: str
    ) -> Dict[str, Any]:
        """Add fingerprint to JWT token data"""
        fingerprint = JWTFingerprint.create_fingerprint(
            user_agent, ip_address, device_id
        )
        
        token_data["fpr"] = fingerprint  # Add fingerprint claim
        return token_data
