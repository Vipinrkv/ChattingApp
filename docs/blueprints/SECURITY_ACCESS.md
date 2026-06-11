# Security & Access Document — ChattingApp

This Security & Access Document defines the security design system, authentication pathways, access controls, error-handling middleware, and edge-case recoveries for **ChattingApp**.

---

## 1. Authentication Method
ChattingApp integrates **Firebase Authentication** as its primary identity provider:
1. **Frontend Flow**: Users authenticate via the Firebase Web SDK (email/password or Google OAuth popup).
2. **Token Exchange**: Upon successful login, the frontend retrieves a Firebase ID Token (JWT).
3. **Backend Flow**: All requests to protected endpoints must include the token in the `Authorization: Bearer <ID_TOKEN>` header.
4. **Token Verification**: FastAPI middleware decodes and verifies the signature of the token using Firebase public keys. If the token is valid, it retrieves the user profile or registers a new user row if it does not exist.

### Active Security Filters
- **IP/Device Reputation Filtering**: Requests from flagged IP addresses are checked against rate limits and blocked if they exhibit abusive behavior.
- **CSRF Protection**: All state-modifying requests (POST, PUT, DELETE) are guarded by CSRF cookie validations, except for requests carrying explicit Firebase authorization tokens.

---

## 2. User Roles & Permissions

The platform uses two layers of access control: **Global Platform Roles** (stored on `users`) and **Group Member Roles** (stored on `group_members`).

### Global Platform Roles
- **Admin**: Full access to dashboard business analytics, health metrics, force shadow-banning, system configurations, and verifying groups or users.
- **User**: Standard permissions. Can create posts, join groups, send messages, and manage their own settings/backups.

### Group Member Roles
- **Owner**: Full control over the group. Can adjust group settings, assign members to Admin/Moderator status, delete the group, and create announcement channels.
- **Admin**: Can kick members, assign Moderator role, edit group metadata, and post announcements.
- **Moderator**: Can review flagged messages, delete offensive content, and approve join requests.
- **Member**: Standard read/write access to group chat rooms and posts.

---

## 3. Row-Level Access Controls (RLAC)

Database models enforce strict user boundaries at the query level. SQLAlchemy filters guarantee that:
- **Direct Messages**: Messages are query-constrained to rows where `sender_id == current_user.id` or `recipient_id == current_user.id`. A user cannot read another user's DMs.
- **Backups**: The chat backup system restricts create, list, and download operations to the owner of the backup archive (`user_id == current_user.id`).
- **User Feed Settings**: Settings in `user_feed_controls` are only visible and modifiable by the corresponding owner.

---

## 4. Error Handling & Response Normalization

All endpoint-level errors are handled by custom FastAPI exception handlers, normalizing all errors into a standard JSON payload containing a `success` flag, a meaningful error message, and a technical code:

```json
{
  "success": false,
  "error": {
    "message": "You are not authorized to access this resource.",
    "code": "unauthorized",
    "details": null
  }
}
```

### Key Exception Handlers
- **APIException**: Catch-all for typed application exceptions (e.g. `InvalidBackupPassphrase`, `RateLimitExceeded`, `GroupAdminApprovalRequired`). Returns specific HTTP codes.
- **RequestValidationError / Pydantic ValidationError**: Catches inputs that violate field schemas. Returns a `422 Unprocessable Entity` with a list of missing or invalid fields.
- **Generic Exception (500)**: Catches unexpected crashes, logs details securely (masking keys), and sends traces to Sentry/OTLP, returning a generic error message.

---

## 5. Edge-Case Recovery Guidelines

### 1. Offline Message Collision
- **Scenario**: A user composes messages while offline, and another device sends conflicting messages.
- **Resolution**: Messages queued in IndexedDB are tagged with unique `client_msg_id` and timestamp values. When the client reconnects, the sync queue flushes them. The server processes them sequentially, ordering them strictly by client-generated timestamps.

### 2. S3 Storage Failure
- **Scenario**: Uploading media to S3 fails due to network outage or credential expiration.
- **Resolution**: The `BaseStorageAdapter` catches S3 exceptions and triggers a local fallback. Files are saved locally to `backend/uploads/` and served via local static paths until the storage provider recovers.

### 3. Media Transcoding Failures
- **Scenario**: An uploaded audio or video file is corrupted, causing FFmpeg to fail.
- **Resolution**: The transcoding processor catches the failure, logs a warning, skips compression, and saves the original raw file directly to ensure the upload is not lost.

---

## 6. Embedded Security & Access Prompt
To generate or iterate on this Security & Access document, use the following prompt:
> "Act as a senior security engineer who specializes in early-stage product security. Create a Security and Access Document for my app. It should cover the authentication method that best fits my use case, all user roles and exactly what each role can and cannot do, row-level security rules for the database, a complete error handling guide for all major failure points, and a list of edge cases I need to handle before launch. My app is a social chatting application featuring Firebase Auth, role-based access, local encrypted backup exports (AES-GCM), and local IndexedDB offline storage queues."
