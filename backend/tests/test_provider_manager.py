# backend/tests/test_provider_manager.py
import pytest
import os
from unittest.mock import MagicMock, patch
from app.core.providers import providers, FirebaseAuthProvider, SupabaseAuthProvider, LocalStorageProvider, MockAIProvider, LocalNotificationProvider, LocalMonitoringProvider

def test_provider_manager_defaults():
    from app.core.config import settings
    # Verify that without specific environment configurations, the defaults or configured fallbacks load correctly
    assert isinstance(providers.ai, MockAIProvider)
    
    if settings.FIREBASE_PROJECT_ID:
        from app.core.providers import FirebaseNotificationProvider
        assert isinstance(providers.notifications, FirebaseNotificationProvider)
    else:
        assert isinstance(providers.notifications, LocalNotificationProvider)

    if settings.SENTRY_DSN:
        from app.core.providers import SentryMonitoringProvider
        assert isinstance(providers.monitoring, SentryMonitoringProvider)
    else:
        assert isinstance(providers.monitoring, LocalMonitoringProvider)

@pytest.mark.asyncio
async def test_local_storage_provider(tmp_path):
    # Test file upload/download/delete using the LocalStorageProvider
    local_provider = LocalStorageProvider(upload_dir=str(tmp_path))
    local_provider.initialize()

    bucket = "test-bucket"
    path = "hello.txt"
    content = b"Hello World"
    content_type = "text/plain"

    # Upload
    url = await local_provider.upload_file(bucket, path, content, content_type)
    assert url == f"/media/{bucket}/{path}"

    # Download
    downloaded = await local_provider.download_file(bucket, path)
    assert downloaded == content

    # Delete
    deleted = await local_provider.delete_file(bucket, path)
    assert deleted is True

    # Confirm deleted
    with pytest.raises(FileNotFoundError):
        await local_provider.download_file(bucket, path)

@pytest.mark.asyncio
async def test_mock_ai_provider():
    ai_provider = MockAIProvider()
    response = await ai_provider.generate_response("Explain quantum physics in one sentence.")
    assert "Explain quantum physics in one" in response
    assert response.startswith("Mock AI auto-response")

@pytest.mark.asyncio
async def test_local_notification_provider():
    notif_provider = LocalNotificationProvider()
    result = await notif_provider.send_notification("token123", "Test Title", "Test Body")
    assert result is True

def test_local_monitoring_provider():
    monitor = LocalMonitoringProvider()
    # Ensure no exception is raised on executing logs
    monitor.capture_message("Hello world message")
    monitor.capture_exception(ValueError("Example Error"))
