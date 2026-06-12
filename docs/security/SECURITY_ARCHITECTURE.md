# Security Architecture

## 1. Overview

Security in ChattingApp spans authentication, authorization, data protection, media safety, and operational controls. The design centers on Firebase identity, backend profile authorization, and secure infrastructure.

## 2. Authentication

- Client: Firebase Auth handles login, signup, and token refresh
- Backend: Firebase Admin SDK verifies ID tokens on every protected request
- Additional backend session mapping is enforced via `users.firebase_uid`

## 3. Authorization

- Backend routes depend on `get_current_user()` to resolve user identity
- Role-based access control is scaffolded with `role` on `users`
- Route-level authorization is enforced through service helpers
- Future design: tenant RBAC and admin isolation policies

## 4. API Protection

- All protected API calls require `Authorization: Bearer <token>`
- CORS origins and allowed hosts are validated with environment settings
- Future needs: rate limiting, abuse protection, throttling, and IP filtering

## 5. WebSocket Security

- WebSocket auth uses the same Firebase token verification as REST
- Connections must be tied to a validated backend user before accepting events
- Future improvements: tenant-aware WebSocket routing, per-user connection limits, and session scoping

## 6. Media and Upload Security

- Upload endpoints validate multipart content on the backend
- Media attachments are stored with safe paths and served through static routes
- Future work: signed upload URLs, MIME validation, malware scanning, and CDN offload

## 7. Data Protection

- Sensitive payloads are encrypted or validated before persistence
- `AES_KEY` and `JWT_SECRET_KEY` are required for encryption workflows
- Future work: database-level encryption, audit logging, and RLS policies

## 8. Infrastructure Security

- Docker and Nginx provide containerized deployment boundaries
- Secrets should be injected through environment variables, not committed
- GitHub Actions uses secrets for Docker Hub credentials and production deployment

## 9. Recommended Security Controls

- Enforce HTTPS and secure headers in production
- Add CSP and HSTS headers on the frontend host
- Add content validation on all upload endpoints
- Audit dependencies with Snyk or similar tooling
- Monitor auth and API abuse with alerts

## 10. Security Checklist

- [ ] Verify Firebase token validation on all protected routes
- [ ] Document required production secrets
- [ ] Add rate limiting protections
- [ ] Enforce strict CORS in production
- [ ] Add audit logging for user actions
- [ ] Add alerts for suspicious activity
