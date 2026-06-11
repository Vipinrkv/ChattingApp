# Centralized Admin Operations Panel

This document outlines the architectural design and operations dashboard layout for the administrative and moderation console.

---

## 1. System Layout & Operations Console

The Admin Console is structured as a dedicated workspace within the ChattingApp frontend, accessible only to accounts with `admin` or `moderator` roles:

```
+--------------------------------------------------------+
|  [Admin Operations Panel]                 User: Admin  |
+--------------------------------------------------------+
|  [Dashboard] [Users] [Reports] [System] [Ads] [Backup] |
+--------------------------------------------------------+
|  System Status Indicators:                             |
|  - PostgreSQL: [Healthy]      - Redis: [Healthy]       |
|  - Sockets:    [142 Active]   - Disk:  [42% Used]      |
+--------------------------------------------------------+
|  Active Moderation Queue:                              |
|  - Report #102: Spam Post by @spammer (Resolve / Keep) |
|  - Verification request: Group "Mohalla Connect" (Appr) |
+--------------------------------------------------------+
```

---

## 2. Admin API Specification

The admin interface requires the following endpoints registered under `/api/v1/admin/` (guarded by `require_moderator` or `require_admin` dependencies):

### A. System Health Endpoint
- **URL**: `GET /api/v1/admin/health`
- **Response**:
  ```json
  {
    "database": "healthy",
    "redis": "healthy",
    "active_websocket_connections": 142,
    "system_cpu_percent": 12.5,
    "disk_utilization_percent": 42.1
  }
  ```

### B. User Management
- **URL**: `GET /api/v1/admin/users?query=xxx`
- **URL**: `POST /api/v1/admin/users/{user_id}/verify`
- **URL**: `POST /api/v1/admin/users/{user_id}/restrict` (updates `is_active` or bans profile)

### C. Backup Operations
- **URL**: `POST /api/v1/admin/backups/trigger` (launches `pg_dump` worker)
- **URL**: `GET /api/v1/admin/backups` (lists available database dumps)

---

## 3. Security & Access Rules

- **Access Level**:
  - `admin`: Full configuration access, backups execution, database exports, and user bans.
  - `moderator`: View-only access to health, resolve/apply moderation actions on reported content, approve group verifications.
- **Verification Logs**: Every change performed in the admin panel logs a deterministic event into `feed_event_chains` to ensure complete traceability.
