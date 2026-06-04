# backend/app/schemas/security.py
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class MFASetupResponse(BaseModel):
    setup_id: str
    qr_code: str
    backup_codes: list[str]
    method: str


class MFAVerifyRequest(BaseModel):
    setup_id: str
    token: str


class SessionResponse(BaseModel):
    session_id: str
    device_name: Optional[str]
    device_type: Optional[str]
    browser: Optional[str]
    os: Optional[str]
    ip_address: Optional[str]
    country: Optional[str]
    city: Optional[str]
    is_trusted: bool
    created_at: str
    last_activity_at: str
    expires_at: str


class SessionRevokeRequest(BaseModel):
    session_id: str


class SessionRevokeAllRequest(BaseModel):
    except_session_id: Optional[str] = None


class SessionCreateRequest(BaseModel):
    device_id: Optional[str] = None
    device_name: Optional[str] = None
    device_type: Optional[str] = None
    browser: Optional[str] = None
    os: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[str] = None
    longitude: Optional[str] = None


class SessionCreateResponse(BaseModel):
    session_id: str
    refresh_token: str
    access_token: str
    expires_in: int


class DeviceTrustRequest(BaseModel):
    device_id: str


class MFAStatusResponse(BaseModel):
    mfa_enabled: bool
    active_methods: list[str]


class AbuseSummaryResponse(BaseModel):
    brute_force_detected: bool
    distributed_attack_sources: list[Dict[str, Any]]
    credential_stuffing_detected: bool
    account_enumeration_detected: bool
    unusual_activity_detected: bool


class LoginHistoryResponse(BaseModel):
    id: str
    status: str
    method: str
    device_name: Optional[str]
    browser: Optional[str]
    os: Optional[str]
    ip_address: str
    country: Optional[str]
    city: Optional[str]
    is_suspicious: bool
    created_at: str


class CSRFTokenResponse(BaseModel):
    csrf_token: str
    expires_at: str


class CSRFVerifyRequest(BaseModel):
    csrf_token: str


class IPReputationResponse(BaseModel):
    ip_address: str
    reputation_score: float
    abuse_score: float
    is_vpn: bool
    is_proxy: bool
    is_datacenter: bool
    is_blacklisted: bool
    country: Optional[str]
    city: Optional[str]
    isp: Optional[str]
    organization: Optional[str]


class AuditLogResponse(BaseModel):
    id: str
    event_type: str
    action: str
    description: Optional[str]
    ip_address: Optional[str]
    created_at: str


class ThreatMetricResponse(BaseModel):
    total_suspicious_activities: int
    blocked_ip_count: int
    active_sessions: int
    recent_failed_logins: int


class SecretRotationResponse(BaseModel):
    jwt_key_id: str
    aes_key_id: str
    instructions: str


class JWTTokenResponse(BaseModel):
    access_token: str
    expires_in: int
