# backend/tests/test_security_hardening.py
import pytest
from jose import jwt as jose_jwt
from datetime import datetime, timezone, timedelta
from app.core.config import settings
from app.core.firebase import FirebaseService
from app.models.session import UserSession, SessionStatus, DeviceType
from app.models.user import User
from app.services.session_service import session_service
import secrets


def test_supabase_jwt_verification_fallback():
    # Set up test secret
    settings.SUPABASE_JWT_SECRET = "my-test-supabase-jwt-secret-key-12345"
    
    # Generate a dummy Supabase JWT
    payload = {
        "sub": "supabase-user-uid-9999",
        "email": "test-supabase@example.com",
        "phone": "+15555550123",
        "user_metadata": {
            "full_name": "Supabase Tester"
        },
        "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())
    }
    token = jose_jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm="HS256")
    
    # Verify the token via FirebaseService (which falls back to Supabase)
    decoded = FirebaseService.verify_token(token)
    
    assert decoded is not None
    assert decoded["uid"] == "supabase-user-uid-9999"
    assert decoded["email"] == "test-supabase@example.com"
    assert decoded["phone_number"] == "+15555550123"
    assert decoded["display_name"] == "Supabase Tester"


@pytest.mark.anyio
async def test_session_refresh_and_rotation_success(session):
    # Create a dummy user
    user = User(
        firebase_uid="firebase-uid-refresh-test",
        username="refresher_user",
        email="refresher@example.com",
        role="user"
    )
    session.add(user)
    await session.flush()
    
    # Create active session for the user
    refresh_token = secrets.token_urlsafe(32)
    access_token = secrets.token_urlsafe(32)
    user_session = UserSession(
        user_id=user.id,
        device_id="device-ref-123",
        device_name="Test Web App",
        device_type=DeviceType.WEB,
        ip_address="127.0.0.1",
        refresh_token_hash=session_service.hash_token(refresh_token),
        access_token_hash=session_service.hash_token(access_token),
        status=SessionStatus.ACTIVE,
        expires_at=datetime.now(timezone.utc) + timedelta(days=10)
    )
    session.add(user_session)
    await session.flush()
    
    # Call refresh_session
    result = await session_service.refresh_session(
        session,
        str(user.id),
        refresh_token,
        ip_address="127.0.0.1",
        user_agent="Mozilla/5.0",
        device_id="device-ref-123"
    )
    
    assert result is not None
    assert result["session_id"] == str(user_session.id)
    assert result["refresh_token"] != refresh_token
    assert result["access_token"] != access_token
    
    # Verify DB state updated
    await session.refresh(user_session)
    assert user_session.refresh_token_hash == session_service.hash_token(result["refresh_token"])
    assert user_session.access_token_hash == session_service.hash_token(result["access_token"])


@pytest.mark.anyio
async def test_session_refresh_device_mismatch_revocation(session):
    # Create a dummy user
    user = User(
        firebase_uid="firebase-uid-refresh-mismatch",
        username="mismatch_user",
        email="mismatch@example.com",
        role="user"
    )
    session.add(user)
    await session.flush()
    
    # Create active session for the user
    refresh_token = secrets.token_urlsafe(32)
    user_session = UserSession(
        user_id=user.id,
        device_id="device-original",
        device_name="Original Device",
        device_type=DeviceType.WEB,
        ip_address="127.0.0.1",
        refresh_token_hash=session_service.hash_token(refresh_token),
        status=SessionStatus.ACTIVE,
        expires_at=datetime.now(timezone.utc) + timedelta(days=10)
    )
    session.add(user_session)
    await session.flush()
    
    # Attempt refresh from a different device
    result = await session_service.refresh_session(
        session,
        str(user.id),
        refresh_token,
        ip_address="127.0.0.1",
        user_agent="Mozilla/5.0",
        device_id="device-malicious-attacker"
    )
    
    assert result is None
    
    # Verify session was revoked automatically for security
    await session.refresh(user_session)
    assert user_session.status == SessionStatus.REVOKED
    assert user_session.revoke_reason == "device_id_mismatch"
