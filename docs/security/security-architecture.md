# ChattingApp - Security Architecture

**Status:** Hardened  
**Target:** Defense-in-Depth

---

## 1. Authentication & Session Security

### 1.1 Dual Identity Provider Auth Flow
ChattingApp integrates a resilient, multi-provider authentication wrapper:
- **Firebase Authentication:** Primary provider for Google OAuth, Email/Password, and Phone OTP.
- **Supabase Authentication Fallback:** In environments where Firebase is unreachable, blocked, or in offline-local mode, the backend validates JWTs signed by Supabase's HS256 credentials.

### 1.2 Session Fingerprinting & Binding
Every authenticated session created via `/api/v1/security/sessions/create` binds:
- User Agent / Browser fingerprint
- Client IP Address
- Device Hardware Fingerprint (`x-device-id`)
Any subsequent API request validates that the request context matches the bounds of the original session token.

### 1.3 Refresh Token Rotation (RTR)
To prevent session hijacking:
- Every token refresh request (`/api/v1/security/sessions/refresh`) invalidates the old refresh token.
- A new access token and a new refresh token are issued in a single atomic transaction.
- If a previously used/revoked refresh token is submitted, the system flags a potential replay attack and automatically revokes all active sessions for that user.

---

## 2. Authorization (RBAC & Permissions)

### 2.1 Role Matrix
User roles are audited on every restricted action:
- `user`: Default. Access to messaging, feed creation, and group participation.
- `moderator`: Access to the moderation reports queue and mute/suspend tools.
- `admin`: Full administrative dashboard, system health logs, role modification, and secret advisories.

### 2.2 Resource Ownership Validation
Endpoints modifying user-generated content (posts, comments, private messages) check that the authenticated user's ID matches the content creator's ID:
```python
if content.user_id != current_user.id and current_user.role != "admin":
    raise PermissionAppError("Resource ownership validation failed")
```

### 2.3 Group-Level Permissions
Groups enforce structured roles:
- `owner`: Can delete group, transfer ownership, assign admins.
- `admin`: Can schedule events, mute/ban members, pin announcements.
- `member`: Can post messages and react (unless group is announcement-only).

---

## 3. API & Web Security

### 3.1 Rate Limiting & Abuse Protection
- **Global limit:** 100 requests per 60 seconds per IP.
- **Auth routes limit:** 20 requests per 60 seconds per IP.
- **Abuse detection:** Automatic threat metrics track failed logins, IP reputation (proxy/VPN checks), credential stuffing, and brute force patterns.

### 3.2 CSRF & XSS Protections
- **CSRF:** Set on HTTP response cookies with `HttpOnly=False`, `Secure=True`, `SameSite=Strict`. Cookie validation is enforced on all mutation routes (POST, PUT, DELETE, PATCH).
- **XSS Sanitization:** Sanitizes HTML input tags on text bodies to prevent script injections.
- **SQL Injection:** Enforced via async SQLAlchemy ORM queries; raw string interpolation in DB queries is strictly forbidden.

---

## 4. Media & Messaging Hardening

### 4.1 Media Scanning & MIME Validation
All uploads to `/api/v1/media` must pass:
- strict MIME type verification (magic number inspections).
- size checks.
- file hashing (MD5/SHA256) to ensure integrity and deduplicate storage.

### 4.2 Messaging Security (E2EE Metadata)
- Private messages are stored encrypted with AES-GCM local keys.
- Local IndexedDB cache on the frontend is fully encrypted using Web Crypto API.
- Backups utilize client-derived passphrase keys to prevent server decryption.
