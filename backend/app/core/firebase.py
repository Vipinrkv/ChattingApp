# backend/app/core/firebase.py
import certifi
import firebase_admin
from firebase_admin import auth, credentials
from typing import Optional, Dict, Any
import logging
import os
import base64
import json
import time
from pathlib import Path
from fastapi import Header, HTTPException, status, Request
from app.core.config import settings

logger = logging.getLogger(__name__)


class FirebaseService:
    _initialized = False

    @classmethod
    def _resolve_credentials_path(cls) -> Optional[str]:
        """Resolve Firebase credentials path - supports relative and absolute paths"""
        if not settings.FIREBASE_CREDENTIALS_PATH:
            return None
        
        cred_path = settings.FIREBASE_CREDENTIALS_PATH
        
        # If already an absolute path, use it as-is
        if os.path.isabs(cred_path):
            return cred_path if os.path.exists(cred_path) else None
        
        # Try relative to current working directory
        if os.path.exists(cred_path):
            return os.path.abspath(cred_path)
        
        # Try relative to the app directory
        app_dir = Path(__file__).parent.parent.parent
        app_relative_path = os.path.join(app_dir, cred_path)
        if os.path.exists(app_relative_path):
            return app_relative_path
        
        # Try relative to the project root
        project_root = Path(__file__).parent.parent.parent.parent
        project_relative_path = os.path.join(project_root, cred_path)
        if os.path.exists(project_relative_path):
            return project_relative_path
        
        logger.warning(f"Firebase credentials file not found at: {cred_path}")
        return None

    @classmethod
    def _ensure_valid_ssl_bundle(cls) -> None:
        """Ensure SSL environment variables point to a valid certifi bundle."""
        valid_bundle = certifi.where()
        for env_var in ("SSL_CERT_FILE", "REQUESTS_CA_BUNDLE"):
            current_value = os.environ.get(env_var)
            if not current_value or not os.path.exists(current_value):
                os.environ[env_var] = valid_bundle
                logger.info(f"Set {env_var} to certifi bundle: {valid_bundle}")

    @classmethod
    def initialize(cls) -> None:
        """Initialize Firebase Admin SDK"""
        if cls._initialized:
            return

        cls._ensure_valid_ssl_bundle()

        try:
            cred_path = cls._resolve_credentials_path()
            app_options = {"projectId": settings.FIREBASE_PROJECT_ID} if settings.FIREBASE_PROJECT_ID else None
            if cred_path:
                logger.info(f"Using Firebase credentials from: {cred_path}")
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred, app_options)
            else:
                logger.info("Initializing Firebase with default credentials (GOOGLE_APPLICATION_CREDENTIALS)")
                firebase_admin.initialize_app(options=app_options)
            cls._initialized = True
            logger.info("Firebase initialized successfully")
        except Exception as exc:
            logger.error(f"Firebase initialization failed: {exc}")
            raise

    @staticmethod
    def _decode_unverified_claims(token: str) -> Dict[str, Any]:
        """Decode JWT claims for diagnostics without trusting them."""
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return {}

            payload = parts[1] + "=" * (-len(parts[1]) % 4)
            return json.loads(base64.urlsafe_b64decode(payload.encode("utf-8")))
        except Exception:
            return {}

    @staticmethod
    def verify_supabase_token(token: str) -> Optional[Dict[str, Any]]:
        """Verify Supabase JWT token as a fallback"""
        if not settings.SUPABASE_JWT_SECRET:
            return None
        try:
            from jose import jwt as jose_jwt
            payload = jose_jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                options={"verify_aud": False}
            )
            return {
                "uid": payload.get("sub"),
                "email": payload.get("email"),
                "phone_number": payload.get("phone"),
                "display_name": payload.get("user_metadata", {}).get("full_name"),
            }
        except Exception as exc:
            logger.warning("Supabase fallback token verification failed: %s", exc)
            return None

    @staticmethod
    def verify_token(token: str) -> Optional[Dict[str, Any]]:
        """Verify Firebase ID token with Supabase fallback"""
        try:
            if FirebaseService._initialized:
                return auth.verify_id_token(token, check_revoked=False)
        except Exception as exc:
            if "Token used too early" in str(exc):
                time.sleep(1.2)
                try:
                    return auth.verify_id_token(token, check_revoked=False)
                except Exception as retry_exc:
                    exc = retry_exc

            claims = FirebaseService._decode_unverified_claims(token)
            logger.warning(
                "Firebase token verification failed: %s; trying Supabase fallback",
                exc
            )
        
        return FirebaseService.verify_supabase_token(token)

    @staticmethod
    def get_user(uid: str) -> Optional[Dict[str, Any]]:
        """Get Firebase user by UID"""
        try:
            user = auth.get_user(uid)
            return {
                "uid": user.uid,
                "email": user.email,
                "phone_number": user.phone_number,
                "display_name": user.display_name,
            }
        except Exception as exc:
            logger.error(f"Failed to get user: {exc}")
            return None


firebase_service = FirebaseService()


def initialize_firebase_app() -> None:
    """Initialize Firebase SDK once"""
    FirebaseService.initialize()


async def get_firebase_uid(
    authorization: Optional[str] = Header(None),
    request: Request = None,
) -> str:
    """Extract Firebase UID from Authorization header"""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
        )

    token = (
        authorization.replace("Bearer ", "")
        if authorization.startswith("Bearer ")
        else authorization
    )
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing token",
        )

    if not FirebaseService._initialized:
        FirebaseService.initialize()

    decoded_token = firebase_service.verify_token(token)
    if not decoded_token or "uid" not in decoded_token:
        # Track and log suspicious auth attempt with request context when available
        client = None
        try:
            client = request.client.host if request and request.client else None
        except Exception:
            client = None

        logger.warning(
            "Suspicious auth attempt: invalid/expired token; client=%s; token_prefix=%s",
            client,
            (token[:8] + '...') if token else None,
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    return decoded_token["uid"]
