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

### 3. Redesign Double-Header Chat Layout (CHAT-01)
- **Description**: Eliminate the oversized, stacked page-level header ("Chat / Messaging") and contact-level header. Integrate them cleanly into the respective panels.
- **Priority**: P0 (Critical)
- **Estimated Effort**: 1 day
- **Dependencies**: None
- **Acceptance Criteria**: Only one header is visible at a time. The Chat list sidebar shows inbox search/filters, and the Chat thread displays contact info.

### 4. Implement Messaging Welcome Empty State (CHAT-02)
- **Description**: Design a modern, professional welcome screen and onboarding instructions when no conversation is selected, rather than auto-selecting the first peer.
- **Priority**: P0 (Critical)
- **Estimated Effort**: 1 day
- **Dependencies**: None
- **Acceptance Criteria**: Shows illustrations, shortcuts, and quick links rather than a blank column or locked user state.

### 5. Create Collapsible Right Contact Details Panel (CHAT-03)
- **Description**: Move the floating shared media gallery and contact info details to a dedicated collapsible right-hand side panel.
- **Priority**: P0 (Critical)
- **Estimated Effort**: 1 day
- **Dependencies**: None
- **Acceptance Criteria**: Clicking the "Info" icon in the chat header toggles the right panel, adjusting the center column size without clipping.

### 6. Resolve SQLite Database Disk Locks on Windows Hosts
- **Description**: Relocate the development SQLite database file from OneDrive-synchronized workspace folder to the system temporary directory during local test execution.
- **Priority**: P0 (Critical)
- **Estimated Effort**: 0.5 days
- **Dependencies**: None
- **Acceptance Criteria**: Pytest test suite runs to completion on local Windows machines without disk lock error interruptions.

### 7. Mitigate Firebase Auth Lock-In with Local JWT Fallback
- **Description**: Build fallback token signing and verification logic inside the authentication service using self-hosted JWT parameters (e.g. Supabase Auth credentials) to bypass Firebase failures.
- **Priority**: P0 (Critical)
- **Estimated Effort**: 3 days
- **Dependencies**: None
- **Acceptance Criteria**: Disabling Firebase settings allows users with local accounts to authenticate and fetch profiles.

---

## 🟡 P1 - High Priority Operational Tasks

### 1. Bind FCM Push Notification Tokens to Device ID Session Fingerprints
- **Description**: Secure push token registration by ensuring that client push tokens are linked directly to their session `device_id` fingerprint in the database, preventing notifications from routing to old sessions.
- **Priority**: P1 (High)
- **Estimated Effort**: 2 days
- **Dependencies**: None
- **Acceptance Criteria**: Session revocation or token rotation automatically unregisters the push notification token bound to that device.

### 2. Centralize Admin Health and Moderation API Endpoints
- **Description**: Expose the backend admin system health query APIs (`GET /api/v1/admin/health`) returning PostgreSQL connection pools, Redis metrics, CPU, disk metrics, and active socket counts.
- **Priority**: P1 (High)
- **Estimated Effort**: 3 days
- **Dependencies**: None
- **Acceptance Criteria**: Admin health endpoints return accurate system stats and reject requests from non-admin accounts with an `HTTP_403_FORBIDDEN`.

### 3. Fix Horizontal Mobile Chat List Carousel (CHAT-04)
- **Description**: Reorganize the horizontal scroll carousel of conversation cards on mobile viewports into a standard vertical scrolling list.
- **Priority**: P1 (High)
- **Estimated Effort**: 1 day
- **Dependencies**: None
- **Acceptance Criteria**: No horizontal scroll on mobile; conversation list scrolls vertically and fits within the thumb zone.

### 4. Implement Chat Composer Media Staging Area (CHAT-05)
- **Description**: Redesign input to support horizontal staging previews of attached media before upload, and collapse caption/message inputs.
- **Priority**: P1 (High)
- **Estimated Effort**: 1 day
- **Dependencies**: None
- **Acceptance Criteria**: Selected attachments show preview thumbnails and description caption fields before sending.

### 5. Implement Redis Cache Degradation Fallbacks
- **Description**: Add connection error handling within the backend `redis_cache.py` service. If Redis becomes temporarily unreachable, queries should fail over directly to PostgreSQL read-only paths and automatically re-try connection checks.
- **Priority**: P1 (High)
- **Estimated Effort**: 1.5 days
- **Dependencies**: None
- **Acceptance Criteria**: Shutting down the Redis service locally does not trigger backend API crashes; requests fallback to querying the database directly.

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

### 3. Mapped Peer-ID Chat Draft Persistence (CHAT-06)
- **Description**: Add support to cache composer text drafts in memory mapped by selected peer ID.
- **Priority**: P2 (Medium)
- **Estimated Effort**: 0.5 days
- **Dependencies**: None
- **Acceptance Criteria**: Switching chats and returning restores the exact draft content in progress.

### 4. Expand Mobile Touch Target Sizes (CHAT-07)
- **Description**: Increase clickable interaction zones for icons (emoji picker, attachment clips, voice recorder) to a minimum of 44px.
- **Priority**: P2 (Medium)
- **Estimated Effort**: 0.5 days
- **Dependencies**: None
- **Acceptance Criteria**: Prevents fat-finger errors on mobile devices.

---

## 🟢 P3 - Low Priority Polish

### 1. CSS Safe-Area Insets for Mobile PWAs
- **Description**: Add CSS safe-area padding-bottom environment variables (`padding-bottom: env(safe-area-inset-bottom)`) to the bottom navigation bar to avoid overlay conflicts with native gestures on iOS Safari.
- **Priority**: P3 (Low)
- **Estimated Effort**: 1 day
- **Dependencies**: None
- **Acceptance Criteria**: The bottom navigation is positioned correctly above browser navigation controls on all mobile viewports.

### 2. Redesign Bubble Tails & Message Grouping (CHAT-08)
- **Description**: Add modern bubble tail indicators and style incoming vs. outgoing bubbles with distinct HSL gradients.
- **Priority**: P3 (Low)
- **Estimated Effort**: 0.5 days
- **Dependencies**: None
- **Acceptance Criteria**: Clear visual delineation of message origin and flow continuity.

---


## 🟢 Completed Tasks (2026-06-11)

### Frontend UI/UX Modernization & Audits
- **Chat Experience**: Added conversation filters, search, pinned/archived storage, presence indicators, sticky date separators, consecutive message grouping, scroll-to-bottom buttons, and popover actions dropdown.
- **Group Experience**: Reorganized layout into tabbed views (Chat, Members, Events, Onboarding steps), added announcement banners, role badges, and onboarding checkbox status checkers.
- **Feed Engagements**: Upgraded Like, Repost, and Comment cards with modern count animations, interactive triggers, skeleton loaders, and comment composers.
- **Profile Hub**: Upgraded preview layout to a 3-column stats block and added a dynamic Security & Trust checklist explaining privacy setting implications.
- **Responsive Layout & Accessibility**: Restructured mobile grid overlay switches, high-contrast tab focuses, and dynamic status ARIA tags.
- **Documentation**: Generated the 8 comprehensive frontend reports under `docs/frontend/`.
