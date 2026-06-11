# Security Report

This report documents the security posture, threat model, and defense-in-depth implementations completed on ChattingApp.

---

## 1. Thread Model & Defenses

- **Brute Force & Abuse**: Mitigated via FastAPI router-level rate limiting (`app/core/middleware.py`).
- **SQL Injection**: Parameterized SQL queries via SQLAlchemy exclude raw SQL manipulations.
- **XSS Attacks**: Frontend escaping using JSX.
- **CSRF Hijacking**: Handled by double-submit cookie checks on state-modifying endpoints.

---

## 2. Session & Auth Verification

- **Supabase/Firebase Dual-Provider Auth**: Verifies tokens against Firebase, falling back to local JWT signature decryption (Supabase) if Firebase is offline.
- **Device Session Fingerprinting**: On login/refresh, the device fingerprint `device_id` is embedded in the session token. Mismatched request fingerprints immediately revoke the session.
- **Refresh Token Rotation (RTR)**: Each refresh token is single-use. Submitting an invalidated token invalidates the entire token family.

---

## 3. Storage & Encryption

- **Message E2EE**: Message payloads are encrypted client-side using AES-GCM before transport.
- **IndexedDB Encrypted Cache**: Client caches feed and chat messages in an encrypted SQLite/IndexedDB environment using user-derived keys.
- **Blockchain-inspired Hashing**: System and moderation logs are linked via SHA-256 event chaining to ensure tamper evidence.
