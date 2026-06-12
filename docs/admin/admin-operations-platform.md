# Admin Operations Platform

This document describes the architectural layout, isolation mechanisms, and security requirements for the Dedicated Admin Operations Application, separating administrative capabilities from standard user channels.

---

## 1. Architectural Isolation Strategy

To minimize attack surfaces and prevent administrative footprints from being exposed to general users:
- **No Shared Frontend Assets:** Administrative navigation, routes, and panels (moderation queues, audit review logs, and system metrics) are completely excluded from the user application build.
- **Separate Frontend Application:** The admin portal is deployed as a distinct, isolated frontend application (e.g. `admin.mychattingapp.com`).
- **Separate Route Space:** The backend separates administrative APIs under a gated routing structure:
  - User APIs: `/api/v1/chat/*`, `/api/v1/posts/*`.
  - Admin APIs: `/api/v1/admin/*` and `/api/v1/moderation/*`.
- **Backend Role Enforcement:** Even if a user guesses admin endpoints, the backend strictly rejects requests lacking the `admin` or `moderator` role claim with a `403 Forbidden`.

---

## 2. Platform Security Constraints

The Admin Operations Platform enforces defense-in-depth controls:

### 2.1 Multi-Factor Authentication (MFA)
- Admin and Moderator accounts MUST authenticate using MFA (TOTP token verification) on every login attempt.
- Standard session authorization tokens are invalid for administrative operations unless the token includes the `mfa_verified` claim.

### 2.2 Role-Based Access Control (RBAC)
The admin platform enforces granular roles:
- **`super_admin`:** Full system control, role modifications, DB backup trigger, and configuration updates.
- **`moderator`:** Resolves user reports, views user risks, and reviews content toxicity blocks.
- **`support_agent`:** View-only rights to user details and device histories to resolve help requests.

### 2.3 Session Tracking & Device Verification
- Session timeout is restricted to 4 hours (compared to 30 days for general users).
- Admin logins require **Device Verification**: if an admin logs in from an unrecognized device fingerprint or a new geographic region, the login is blocked until approved via an out-of-band security email or OTP code.

### 2.4 Audit Logging
- Every click, query, moderation action (e.g., shadow-banning a post or resetting a password), and configuration edit is logged to the immutable audit ledger.
- Logs include: `admin_id`, `client_ip`, `user_agent`, `timestamp`, `action`, `target_id`, and `audit_signature`.

---

## 3. Network Isolation Options

To further protect administrative infrastructure:
- **IP Restrictions:** The admin portal API gateway enforces IP white-listing, allowing requests only from verified corporate IPs.
- **VPN / Private Network Access:** Admin routes can be configured to reject external traffic entirely, routing admin traffic exclusively through a private corporate VPN or Virtual Private Cloud (VPC) network.
- **No Admin Indication in DNS:** The subdomain name can be randomized (e.g. `op-portal-a7d.mychattingapp.com`) to hide administrative portals from public network scanners.
