# Remaining Gaps Report

This report identifies remaining technical gaps, production readiness considerations, and recommendations for future iterations of the ChattingApp platform.

---

## 1. WebRTC Production-Grade Calling (TURN/STUN)

- **Gap**: Voice and video calling function in local/LAN environments. However, in production environments with restrictive firewalls and Symmetric NATs, direct peer-to-peer WebRTC connections will fail.
- **Resolution**: Deploy a self-hosted **coturn** TURN/STUN server. The TURN configuration must be added to the frontend WebRTC initialization parameters:
  ```typescript
  const peerConnection = new RTCPeerConnection({
    iceServers: [
      { urls: 'stun:stun.l.google.com:19302' },
      {
        urls: 'turn:turn.mychattingapp.com:3478',
        username: 'turn_user',
        credential: 'turn_password'
      }
    ]
  });
  ```

---

## 2. Server-Side Media Retention & Auto-Cleanup

- **Gap**: The media service saves uploads locally or to a MinIO bucket. Over time, expired temporary files or deleted messages can leave orphaned media records, filling up host server disk space.
- **Resolution**: Implement a background task (managed by Celery/RQ) that runs daily to:
  1. Scan the local `uploads/` directory.
  2. Verify if the file hash exists in the `shared_media_galleries` database table.
  3. Safe-delete any orphaned files that have no database references.

---

## 3. Observability and Monitoring Dashboards

- **Gap**: While the backend exports OTel traces and metrics, the production Grafana dashboard requires manual setup.
- **Resolution**: Package a pre-configured Grafana dashboard JSON template (`grafana/dashboards/chattingapp.json`) containing panels for:
  - Active WebSocket connections count.
  - HTTP request error rates (5xx, 4xx).
  - Database pool utilization and query response times.
  - Redis connection status.
