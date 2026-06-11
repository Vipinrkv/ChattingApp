# ChattingApp Priority TODO list

This checklist details the outstanding tasks for production release, sorted by priority and risk profile.

---

## 🔴 P0 - Critical Release Blockers

### 1. Deploy Production TURN/STUN (coturn) Server
- **Description**: Configure a production TURN/STUN relay server for WebRTC peer-to-peer connection traversal through strict symmetric NATs and firewalls.
- **Priority**: P0 (Critical)
- **Estimated Effort**: 3 days
- **Dependencies**: None
- **Acceptance Criteria**: WebRTC calling connects successfully between peers located on different firewalled networks.

### 2. Implement Server-Side Media Retention and Auto-Cleanup
- **Description**: Implement a daily background cleanup task that checks the local uploads and S3 directories for orphaned files (files with no database reference in the `shared_media_galleries` table) and deletes them.
- **Priority**: P0 (Critical)
- **Estimated Effort**: 2 days
- **Dependencies**: None
- **Acceptance Criteria**: Running the clean task successfully identifies and removes deleted message media files from storage without affecting active media.

---

## 🟡 P1 - High Priority Operational Tasks

### 1. Bind FCM Push Notification Tokens to Device ID Session Fingerprints
- **Description**: Secure push token registration by ensuring that client push tokens are linked directly to their session `device_id` fingerprint in the database, preventing notifications from routing to old sessions.
- **Priority**: P1 (High)
- **Estimated Effort**: 2 days
- **Dependencies**: None
- **Acceptance Criteria**: Session revocation or token rotation automatically unregisters the push notification token bound to that device.

### 2. centralize Admin Health and Moderation API Endpoints
- **Description**: Expose the backend admin system health query APIs (`GET /api/v1/admin/health`) returning PostgreSQL connection pools, Redis metrics, CPU, disk metrics, and active socket counts.
- **Priority**: P1 (High)
- **Estimated Effort**: 3 days
- **Dependencies**: None
- **Acceptance Criteria**: Admin health endpoints return accurate system stats and reject requests from non-admin accounts with an `HTTP_403_FORBIDDEN`.

---

## 🔵 P2 - Medium Priority Features

### 1. Build Sponsored Post Placement Routing & Database Schemas
- **Description**: Implement sponsored post schemas and ad placement endpoints to allow targeted native feed delivery based on user interest graphs.
- **Priority**: P2 (Medium)
- **Estimated Effort**: 4 days
- **Dependencies**: None
- **Acceptance Criteria**: Native ads are delivered to the frontend feed at a ratio of 1 ad per 10 organic posts.

### 2. Package Grafana Observability Dashboards
- **Description**: Create Grafana dashboard JSON configurations for scraping active socket counts, cache hit metrics, HTTP error rates, and query latencies.
- **Priority**: P2 (Medium)
- **Estimated Effort**: 2 days
- **Dependencies**: Centralized Admin Health APIs
- **Acceptance Criteria**: Grafana dashboard imports successfully and visualizes Prometheus telemetry.

---

## 🟢 P3 - Low Priority Polish

### 1. CSS Safe-Area Insets for Mobile PWAs
- **Description**: Add CSS safe-area padding-bottom environment variables (`padding-bottom: env(safe-area-inset-bottom)`) to the bottom navigation bar to avoid overlay conflicts with native gestures on iOS Safari.
- **Priority**: P3 (Low)
- **Estimated Effort**: 1 day
- **Dependencies**: None
- **Acceptance Criteria**: The bottom navigation is positioned correctly above browser navigation controls on all mobile viewports.

---

## 🟢 Completed Tasks (2026-06-11)

### Frontend UI/UX Modernization & Audits
- **Chat Experience**: Added conversation filters, search, pinned/archived storage, presence indicators, sticky date separators, consecutive message grouping, scroll-to-bottom buttons, and popover actions dropdown.
- **Group Experience**: Reorganized layout into tabbed views (Chat, Members, Events, Onboarding steps), added announcement banners, role badges, and onboarding checkbox status checkers.
- **Feed Engagements**: Upgraded Like, Repost, and Comment cards with modern count animations, interactive triggers, skeleton loaders, and comment composers.
- **Profile Hub**: Upgraded preview layout to a 3-column stats block and added a dynamic Security & Trust checklist explaining privacy setting implications.
- **Responsive Layout & Accessibility**: Restructured mobile grid overlay switches, high-contrast tab focuses, and dynamic status ARIA tags.
- **Documentation**: Generated the 8 comprehensive frontend reports under `docs/frontend/`.
