# backend/app/core/providers.py
import os
import uuid
import logging
from typing import Any, Dict, Optional, Protocol

from app.core.config import settings

logger = logging.getLogger(__name__)

# --- PROVIDER INTERFACES ---

class AuthProvider(Protocol):
    def initialize(self) -> None:
        ...
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        ...
    def get_user(self, uid: str) -> Optional[Dict[str, Any]]:
        ...

class StorageProvider(Protocol):
    def initialize(self) -> None:
        ...
    async def upload_file(self, bucket: str, path: str, data: bytes, content_type: str) -> str:
        ...
    async def download_file(self, bucket: str, path: str) -> bytes:
        ...
    async def delete_file(self, bucket: str, path: str) -> bool:
        ...

class NotificationProvider(Protocol):
    def initialize(self) -> None:
        ...
    async def send_notification(self, token: str, title: str, body: str, data: Optional[Dict[str, Any]] = None) -> bool:
        ...

class MonitoringProvider(Protocol):
    def initialize(self) -> None:
        ...
    def capture_exception(self, exc: Exception, context: Optional[Dict[str, Any]] = None) -> None:
        ...
    def capture_message(self, message: str, level: str = "info", context: Optional[Dict[str, Any]] = None) -> None:
        ...

class AIProvider(Protocol):
    def initialize(self) -> None:
        ...
    async def generate_response(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        ...


# --- PROVIDER IMPLEMENTATIONS ---

# 1. Auth Provider Implementations
class FirebaseAuthProvider(AuthProvider):
    def initialize(self) -> None:
        from app.core.firebase import FirebaseService
        FirebaseService.initialize()

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        from app.core.firebase import FirebaseService
        return FirebaseService.verify_token(token)

    def get_user(self, uid: str) -> Optional[Dict[str, Any]]:
        from app.core.firebase import FirebaseService
        return FirebaseService.get_user(uid)

class SupabaseAuthProvider(AuthProvider):
    def initialize(self) -> None:
        pass

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        from app.core.firebase import FirebaseService
        return FirebaseService.verify_supabase_token(token)

    def get_user(self, uid: str) -> Optional[Dict[str, Any]]:
        return {"uid": uid, "email": f"user_{uid}@supabase.local"}


# 2. Storage Provider Implementations
class LocalStorageProvider(StorageProvider):
    def __init__(self, upload_dir: str = "uploads") -> None:
        self.upload_dir = upload_dir

    def initialize(self) -> None:
        os.makedirs(self.upload_dir, exist_ok=True)

    async def upload_file(self, bucket: str, path: str, data: bytes, content_type: str) -> str:
        full_dir = os.path.join(self.upload_dir, bucket)
        os.makedirs(full_dir, exist_ok=True)
        full_path = os.path.join(full_dir, path)
        with open(full_path, "wb") as f:
            f.write(data)
        return f"/media/{bucket}/{path}"

    async def download_file(self, bucket: str, path: str) -> bytes:
        full_path = os.path.join(self.upload_dir, bucket, path)
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"Local file not found at: {full_path}")
        with open(full_path, "rb") as f:
            return f.read()

    async def delete_file(self, bucket: str, path: str) -> bool:
        full_path = os.path.join(self.upload_dir, bucket, path)
        if os.path.exists(full_path):
            os.remove(full_path)
            return True
        return False

class S3StorageProvider(StorageProvider):
    def initialize(self) -> None:
        try:
            import boto3
            self.boto3 = boto3
        except ImportError:
            raise RuntimeError("boto3 package is required for S3StorageProvider")

    async def upload_file(self, bucket: str, path: str, data: bytes, content_type: str) -> str:
        client = self.boto3.client(
            "s3",
            region_name=settings.AWS_S3_REGION or None,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID or None,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY or None,
        )
        key = f"media/{path}"
        client.put_object(Bucket=bucket, Key=key, Body=data, ContentType=content_type)
        if settings.CDN_URL:
            return settings.CDN_URL.rstrip("/") + f"/{key}"
        region = settings.AWS_S3_REGION or "us-east-1"
        return f"https://{bucket}.s3.{region}.amazonaws.com/{key}"

    async def download_file(self, bucket: str, path: str) -> bytes:
        client = self.boto3.client(
            "s3",
            region_name=settings.AWS_S3_REGION or None,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID or None,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY or None,
        )
        key = f"media/{path}"
        response = client.get_object(Bucket=bucket, Key=key)
        return response["Body"].read()

    async def delete_file(self, bucket: str, path: str) -> bool:
        client = self.boto3.client(
            "s3",
            region_name=settings.AWS_S3_REGION or None,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID or None,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY or None,
        )
        key = f"media/{path}"
        try:
            client.delete_object(Bucket=bucket, Key=key)
            return True
        except Exception as exc:
            logger.error("Failed to delete S3 object: %s", exc)
            return False


# 3. Notification Provider Implementations
class FirebaseNotificationProvider(NotificationProvider):
    def initialize(self) -> None:
        from app.core.firebase import FirebaseService
        FirebaseService.initialize()

    async def send_notification(self, token: str, title: str, body: str, data: Optional[Dict[str, Any]] = None) -> bool:
        try:
            from firebase_admin import messaging
            message = messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                data=data or {},
                token=token
            )
            messaging.send(message)
            return True
        except Exception as exc:
            logger.error("FCM Notification failed: %s", exc)
            return False

class LocalNotificationProvider(NotificationProvider):
    def initialize(self) -> None:
        pass

    async def send_notification(self, token: str, title: str, body: str, data: Optional[Dict[str, Any]] = None) -> bool:
        logger.info("Local notification sent to %s: [%s] %s", token, title, body)
        return True


# 4. Monitoring Provider Implementations
class SentryMonitoringProvider(MonitoringProvider):
    def initialize(self) -> None:
        try:
            import sentry_sdk
            self.sentry_sdk = sentry_sdk
        except ImportError:
            raise RuntimeError("sentry-sdk package is required for SentryMonitoringProvider")
        if settings.SENTRY_DSN:
            self.sentry_sdk.init(dsn=settings.SENTRY_DSN)

    def capture_exception(self, exc: Exception, context: Optional[Dict[str, Any]] = None) -> None:
        with self.sentry_sdk.configure_scope() as scope:
            if context:
                for k, v in context.items():
                    scope.set_extra(k, v)
            self.sentry_sdk.capture_exception(exc)

    def capture_message(self, message: str, level: str = "info", context: Optional[Dict[str, Any]] = None) -> None:
        self.sentry_sdk.capture_message(message, level=level)

class LocalMonitoringProvider(MonitoringProvider):
    def initialize(self) -> None:
        pass

    def capture_exception(self, exc: Exception, context: Optional[Dict[str, Any]] = None) -> None:
        logger.error("Local Captured Exception: %s; Context: %s", exc, context, exc_info=exc)

    def capture_message(self, message: str, level: str = "info", context: Optional[Dict[str, Any]] = None) -> None:
        logger.info("Local Captured Message [%s]: %s; Context: %s", level, message, context)


# 5. AI Provider Implementations
class GeminiAIProvider(AIProvider):
    def initialize(self) -> None:
        pass

    async def generate_response(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        # Placeholder for Gemini SDK or HTTP request integration
        return f"Gemini response for: {prompt}"

class MockAIProvider(AIProvider):
    def initialize(self) -> None:
        pass

    async def generate_response(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        return f"Mock AI auto-response to: {prompt[:30]}"


# --- CENTRAL PROVIDER MANAGER ---

class ExternalProviderManager:
    def __init__(self) -> None:
        self._auth_provider: Optional[AuthProvider] = None
        self._storage_provider: Optional[StorageProvider] = None
        self._notification_provider: Optional[NotificationProvider] = None
        self._monitoring_provider: Optional[MonitoringProvider] = None
        self._ai_provider: Optional[AIProvider] = None

    @property
    def auth(self) -> AuthProvider:
        if not self._auth_provider:
            if settings.SUPABASE_JWT_SECRET and not settings.FIREBASE_PROJECT_ID:
                self._auth_provider = SupabaseAuthProvider()
            else:
                self._auth_provider = FirebaseAuthProvider()
            self._auth_provider.initialize()
        return self._auth_provider

    @property
    def storage(self) -> StorageProvider:
        if not self._storage_provider:
            if settings.AWS_S3_BUCKET:
                self._storage_provider = S3StorageProvider()
            else:
                self._storage_provider = LocalStorageProvider()
            self._storage_provider.initialize()
        return self._storage_provider

    @property
    def notifications(self) -> NotificationProvider:
        if not self._notification_provider:
            if settings.FIREBASE_PROJECT_ID:
                self._notification_provider = FirebaseNotificationProvider()
            else:
                self._notification_provider = LocalNotificationProvider()
            self._notification_provider.initialize()
        return self._notification_provider

    @property
    def monitoring(self) -> MonitoringProvider:
        if not self._monitoring_provider:
            if settings.SENTRY_DSN:
                self._monitoring_provider = SentryMonitoringProvider()
            else:
                self._monitoring_provider = LocalMonitoringProvider()
            self._monitoring_provider.initialize()
        return self._monitoring_provider

    @property
    def ai(self) -> AIProvider:
        if not self._ai_provider:
            if os.environ.get("GEMINI_API_KEY"):
                self._ai_provider = GeminiAIProvider()
            else:
                self._ai_provider = MockAIProvider()
            self._ai_provider.initialize()
        return self._ai_provider


providers = ExternalProviderManager()
