# Admin Panel Report

This report outlines the layout, access controls, and functional capabilities designed for the Admin Operations Panel.

---

## 1. Capabilities
- **System Monitoring**: Tracks database query times, Redis health, CPU, disk usage, and active WebSocket connection counts.
- **Content Moderation**: Centralized view for post/comment reports and verification requests for groups.
- **Operations & Backups**: Triggers database backups, lists files on disk, and tracks moderation actions using linked SHA-256 logs.

---

## 2. Access Controls
- Enforces Role-Based Access Control (RBAC) via the backend auth layer.
- **admin** role has full configuration, backup execution, and user restriction powers.
- **moderator** role is limited to viewing dashboards and resolving content reports.
