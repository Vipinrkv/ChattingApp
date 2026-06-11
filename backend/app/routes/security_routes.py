# backend/app/routes/security_routes.py
from datetime import timedelta, datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.auth import get_current_user as get_current_user_dep
from app.core.config import settings
from app.core.security import security_service
from app.core.jwt_fingerprint import JWTFingerprint
from app.database.connection import get_db_session
from app.models.login_history import LoginHistory, LoginStatus
from app.models.ip_reputation import IPReputation
from app.models.session import UserSession
import secrets
from app.models.security_audit import SecurityAudit
from app.schemas.security import (
    MFASetupResponse,
    MFAVerifyRequest,
    MFAStatusResponse,
    SessionResponse,
    SessionCreateRequest,
    SessionCreateResponse,
    SessionRefreshRequest,
    SessionRevokeRequest,
    SessionRevokeAllRequest,
    DeviceTrustRequest,
    LoginHistoryResponse,
    CSRFTokenResponse,
    CSRFVerifyRequest,
    IPReputationResponse,
    AbuseSummaryResponse,
    AuditLogResponse,
    ThreatMetricResponse,
    SecretRotationResponse,
    JWTTokenResponse,
)
from app.services.mfa_service import mfa_service
from app.services.session_service import session_service
from app.services.csrf_service import csrf_service
from app.services.ip_reputation_service import ip_reputation_service
from app.services.security_audit_service import security_audit_service
from app.services.login_history_service import login_history_service
from app.services.abuse_detection_service import abuse_detection_service
from app.models.user import User
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_request_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _get_device_info(request: Request) -> dict:
    return {
        "device_name": request.headers.get("x-device-name"),
        "device_type": request.headers.get("x-device-type"),
        "browser": request.headers.get("user-agent"),
        "os": request.headers.get("x-device-os"),
        "user_agent": request.headers.get("user-agent"),
    }


@router.get("/mfa/setup", response_model=MFASetupResponse)
async def prepare_mfa_setup(
    request: Request,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    """Prepare MFA enrollment with TOTP QR code."""
    result = await mfa_service.create_totp_setup(
        session, str(current_user.id), issuer=settings.APP_NAME
    )
    await security_audit_service.log_event(
        session,
        event_type="mfa_setup_requested",
        action="created",
        user_id=str(current_user.id),
        ip_address=_get_request_ip(request),
        user_agent=request.headers.get("user-agent"),
        description="User requested MFA enrollment setup",
    )
    return result


@router.post("/mfa/verify")
async def verify_mfa_setup(
    request: Request,
    payload: MFAVerifyRequest,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    """Verify MFA setup with one-time password token."""
    success = await mfa_service.verify_totp(
        session, str(current_user.id), payload.setup_id, payload.token
    )
    if not success:
        await login_history_service.record_login_attempt(
            session,
            user_id=str(current_user.id),
            status=LoginStatus.FAILED,
            method="mfa",
            identifier=str(current_user.email or current_user.phone or current_user.username),
            ip_address=_get_request_ip(request),
            device_info=_get_device_info(request),
            failure_reason="Invalid MFA token",
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid MFA token",
        )

    await security_audit_service.log_event(
        session,
        event_type="mfa_verified",
        action="verified",
        user_id=str(current_user.id),
        ip_address=_get_request_ip(request),
        user_agent=request.headers.get("user-agent"),
        description="User verified MFA setup",
    )
    return {"success": True}


@router.get("/mfa/status", response_model=MFAStatusResponse)
async def get_mfa_status(
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    """Return the current MFA enrollment status for the authenticated user."""
    active_methods = await mfa_service.get_active_mfa_methods(session, str(current_user.id))
    mfa_enabled = len(active_methods) > 0
    return {"mfa_enabled": mfa_enabled, "active_methods": [method.value for method in active_methods]}


@router.post("/sessions/create", response_model=SessionCreateResponse)
async def create_session(
    request: Request,
    payload: SessionCreateRequest,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    """Create a new session for the authenticated user."""
    ip_address = _get_request_ip(request)
    device_id = payload.device_id or request.headers.get("x-device-id", ip_address)
    device_info = {
        "device_id": device_id,
        "device_name": payload.device_name,
        "device_type": payload.device_type,
        "browser": payload.browser or request.headers.get("user-agent"),
        "os": payload.os,
        "user_agent": request.headers.get("user-agent"),
        "country": payload.country,
        "city": payload.city,
        "latitude": payload.latitude,
        "longitude": payload.longitude,
    }

    result = await session_service.create_session(
        session,
        str(current_user.id),
        device_id,
        ip_address,
        device_info,
    )

    await login_history_service.record_login_attempt(
        session,
        user_id=str(current_user.id),
        status=LoginStatus.SUCCESS,
        method="session",
        identifier=str(current_user.email or current_user.username or str(current_user.id)),
        ip_address=ip_address,
        device_info=device_info,
    )

    await ip_reputation_service.record_successful_login(session, ip_address)

    await security_audit_service.log_event(
        session,
        event_type="session_created",
        action="created",
        user_id=str(current_user.id),
        ip_address=ip_address,
        user_agent=request.headers.get("user-agent"),
        description="User created a new session",
        metadata={"device_id": device_id},
    )

    return result


@router.post("/sessions/refresh", response_model=SessionCreateResponse)
async def refresh_session(
    request: Request,
    payload: SessionRefreshRequest,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    """Refresh active session and rotate tokens."""
    ip_address = _get_request_ip(request)
    result = await session_service.refresh_session(
        session,
        str(current_user.id),
        payload.refresh_token,
        ip_address,
        request.headers.get("user-agent", ""),
        payload.device_id,
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token or device mismatch",
        )
    return result


@router.post("/devices/trust")
async def trust_device(
    payload: DeviceTrustRequest,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    """Mark a device as trusted for the authenticated user."""
    success = await session_service.trust_device(session, payload.device_id, str(current_user.id))
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")

    await security_audit_service.log_event(
        session,
        event_type="device_trusted",
        action="updated",
        user_id=str(current_user.id),
        description=f"Device {payload.device_id} trusted by user",
    )
    return {"success": True}


@router.get("/abuse/summary", response_model=AbuseSummaryResponse)
async def abuse_summary(
    request: Request,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    """Return abuse detection insights from recent login and security events."""
    identifier = str(current_user.email or current_user.username or str(current_user.id))
    brute_force_detected = await abuse_detection_service.check_brute_force_attack(
        session,
        identifier,
    )
    distributed_attack_sources = await abuse_detection_service.check_distributed_attack(session)
    credential_stuffing_detected = await abuse_detection_service.check_credential_stuffing(
        session,
        _get_request_ip(request),
    )
    account_enumeration_detected = await abuse_detection_service.check_account_enumeration(session)
    unusual_activity_detected = await abuse_detection_service.check_unusual_activity(
        session,
        str(current_user.id),
    )

    await security_audit_service.log_event(
        session,
        event_type="abuse_summary_requested",
        action="viewed",
        user_id=str(current_user.id),
        ip_address=_get_request_ip(request),
        user_agent=request.headers.get("user-agent"),
        description="User requested abuse summary insights",
    )

    return {
        "brute_force_detected": brute_force_detected,
        "distributed_attack_sources": distributed_attack_sources,
        "credential_stuffing_detected": credential_stuffing_detected,
        "account_enumeration_detected": account_enumeration_detected,
        "unusual_activity_detected": unusual_activity_detected,
    }


@router.get("/sessions", response_model=list[SessionResponse])
async def get_sessions(
    request: Request,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    """Return active sessions for the current user."""
    sessions = await session_service.get_active_sessions(session, str(current_user.id))
    return sessions


@router.post("/sessions/revoke")
async def revoke_session(
    current_user: User = Depends(get_current_user_dep),
    payload: SessionRevokeRequest = Depends(),
    session: AsyncSession = Depends(get_db_session),
):
    """Revoke a single user session."""
    success = await session_service.revoke_session(session, payload.session_id, reason="user_revoked")
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return {"success": True}


@router.post("/sessions/revoke-all")
async def revoke_all_sessions(
    current_user: User = Depends(get_current_user_dep),
    payload: SessionRevokeAllRequest = Depends(),
    session: AsyncSession = Depends(get_db_session),
):
    """Revoke all sessions for the current user."""
    count = await session_service.revoke_all_sessions(
        session, str(current_user.id), except_session_id=payload.except_session_id
    )
    return {"success": True, "revoked_count": count}


@router.get("/login-history", response_model=list[LoginHistoryResponse])
async def login_history(
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    """Return recent login events for the current user."""
    entries = await login_history_service.get_recent_logins(session, str(current_user.id))
    return entries


@router.post("/csrf/token", response_model=CSRFTokenResponse)
async def create_csrf_token(
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    """Issue a fresh CSRF token for the current user."""
    token = await csrf_service.create_token(
        session,
        user_id=str(current_user.id),
        expires_delta=timedelta(hours=1),
    )
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    response = JSONResponse(
        {"csrf_token": token, "expires_at": expires_at.isoformat()}
    )
    response.set_cookie(
        key=settings.CSRF_COOKIE_NAME,
        value=token,
        secure=settings.COOKIE_SECURE,
        httponly=False,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.CSRF_COOKIE_MAX_AGE_SECONDS,
        path="/",
    )
    return response


@router.post("/csrf/verify")
async def verify_csrf_token(
    payload: CSRFVerifyRequest,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    """Verify a CSRF token from the client."""
    verified = await csrf_service.verify_token(session, payload.csrf_token, user_id=str(current_user.id))
    if not verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token")
    return {"success": True}


@router.get("/ip-reputation", response_model=IPReputationResponse)
async def ip_reputation(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
):
    """Get reputation data for the current request IP."""
    ip_address = _get_request_ip(request)
    data = await ip_reputation_service.get_reputation(session, ip_address)
    return data


@router.get("/audit-logs", response_model=list[AuditLogResponse])
async def audit_logs(
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    """Return recent security audit logs for the current user."""
    logs = await security_audit_service.get_user_audit_logs(session, str(current_user.id))
    return logs


@router.get("/threat-dashboard", response_model=ThreatMetricResponse)
async def threat_dashboard(
    session: AsyncSession = Depends(get_db_session),
):
    """Return aggregated threat metrics for monitoring."""
    suspicious_count = await session.scalar(select(func.count()).select_from(SecurityAudit).where(SecurityAudit.event_type == "suspicious_activity"))
    blocked_ip_count = await session.scalar(select(func.count()).select_from(IPReputation).where(IPReputation.is_blacklisted == True))
    active_sessions = await session.scalar(select(func.count()).select_from(UserSession).where(UserSession.status == "active"))
    recent_failed_logins = await session.scalar(
        select(func.count()).select_from(LoginHistory).where(
            LoginHistory.status == LoginStatus.FAILED,
            LoginHistory.created_at >= datetime.now(timezone.utc) - timedelta(hours=24),
        )
    )
    return {
        "total_suspicious_activities": int(suspicious_count or 0),
        "blocked_ip_count": int(blocked_ip_count or 0),
        "active_sessions": int(active_sessions or 0),
        "recent_failed_logins": int(recent_failed_logins or 0),
    }


@router.post("/secret-rotation", response_model=SecretRotationResponse)
async def rotate_secrets(
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    """Create a secret rotation advisory batch for JWT and AES keys."""
    jwt_key_id = secrets.token_hex(16)
    aes_key_id = secrets.token_hex(16)
    instructions = (
        "Rotate secrets by updating the environment variables JWT_SECRET_KEY and AES_KEY. "
        "Persist the old secret version in a secure vault and update application instances one-at-a-time. "
        "Use a staging rollout to validate new secrets before full production deployment."
    )
    await security_audit_service.log_event(
        session,
        event_type="secret_rotation",
        action="requested",
        user_id=str(current_user.id),
        description="Requested secret rotation advisory.",
    )
    return {
        "jwt_key_id": jwt_key_id,
        "aes_key_id": aes_key_id,
        "instructions": instructions,
    }


@router.post("/jwt/issue", response_model=JWTTokenResponse)
async def issue_jwt_token(
    request: Request,
    current_user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_db_session),
):
    """Issue a fingerprinted JWT for the current session."""
    ip_address = _get_request_ip(request)
    device_id = request.headers.get("x-device-id", ip_address)
    token = security_service.create_access_token_with_fingerprint(
        {
            "sub": str(current_user.id),
            "email": current_user.email,
            "username": current_user.username,
        },
        request.headers.get("user-agent", ""),
        ip_address,
        device_id,
        expires_delta=timedelta(hours=settings.JWT_EXPIRATION_HOURS),
    )
    await security_audit_service.log_event(
        session,
        event_type="jwt_issued",
        action="issued",
        user_id=str(current_user.id),
        ip_address=ip_address,
        user_agent=request.headers.get("user-agent"),
        description="Issued fingerprinted JWT",
    )
    return {"access_token": token, "expires_in": settings.JWT_EXPIRATION_HOURS * 3600}


@router.post("/jwt/verify")
async def verify_jwt_token(
    request: Request,
    token: str,
):
    """Verify fingerprinted JWT from the request or payload."""
    ip_address = _get_request_ip(request)
    device_id = request.headers.get("x-device-id", ip_address)
    payload = security_service.verify_token_with_fingerprint(
        token,
        request.headers.get("user-agent", ""),
        ip_address,
        device_id,
    )
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or mismatched JWT fingerprint")
    return {"success": True, "payload": payload}
