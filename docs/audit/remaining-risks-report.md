# Remaining Risks Report

This report documents the remaining risks and technical debt identified during the production readiness audit of ChattingApp.

---

## 1. TURN/STUN Relay Dependency (WebRTC Calling)
- **Risk**: Without Coturn servers deployed in production, mobile voice/video calls will fail to connect when users are behind symmetric corporate firewalls or carrier-grade NATs.
- **Severity**: High
- **Mitigation**: Deploy self-hosted `coturn` instances on cloud VMs, configure auth credentials, and update the client peer connection ICE servers.

---

## 2. Server Disk Exhaustion (Orphaned Media)
- **Risk**: Deleting messages deletes database references, but leaves media uploads in `/uploads` or object storage, slowly filling up server storage.
- **Severity**: Medium
- **Mitigation**: Set up a daily cron task to query the database, cross-reference files on disk, and purge any orphaned uploads.

---

## 3. Dynamic Push Notification Scaling
- **Risk**: If the platform has millions of active mobile clients, pushing notifications sequentially on the web process will block request threads.
- **Severity**: Medium
- **Mitigation**: Offload notification requests to background workers (Celery/RQ) using dedicated worker nodes.

---

## 4. IP Geolocation Database Updates
- **Risk**: Targeted advertising and security checks rely on MaxMind IP geolocation databases. If not updated, client location targeting will drift.
- **Severity**: Low
- **Mitigation**: Set up an automated weekly script to download the latest MaxMind GeoLite2 databases.
