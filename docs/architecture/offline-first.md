# ChattingApp - Offline-First Reliability Architecture

ChattingApp employs a local-first design to ensure messaging and social interaction functions seamlessly under poor or zero network connectivity, reconciling state automatically upon reconnection.

---

## 1. Local Caching & IndexedDB Schema

The client leverages IndexedDB (wrapped via a lightweight store wrapper) to persist critical app states:

### 1.1 Data Stores
- **`user_profile`:** Caches the authenticated user's profile and settings.
- **`friends_list`:** Caches mutual friend connections and suggested users.
- **`chat_conversations`:** Stores direct and group message threads (recent 100 messages per thread) for instant offline loading.
- **`offline_outbox`:** The queue storing actions to be synced once connectivity is restored.

---

## 2. Offline Action Queue & Idempotency

When the client is offline (detected via `navigator.onLine` or API timeout events), user actions are not blocked. Instead, they are appended to the `offline_outbox` store.

### 2.1 Action Types
- `CREATE_MESSAGE`: Queue chat messages.
- `CREATE_POST`: Queue social feed posts.
- `TOGGLE_LIKE`: Queue feed reactions/likes.
- `UPDATE_PROFILE`: Queue bio/username edits.

### 2.2 Client-Generated UUIDs
To prevent duplicate operations upon retry:
- Every message and post created offline is assigned a client-side UUID.
- The backend checks for the presence of this UUID in database constraints (or Redis caches) to ensure **idempotency**.

---

## 3. Sync Reconciliation & Conflict Resolution

Upon network restoration, the sync engine is triggered:

```
[Network Restored]
        │
        ▼
[Read offline_outbox] ──► (Empty?) ──► [Done]
        │ (Has Actions)
        ▼
[Process FIFO Queue]
   For each action:
     - Submit HTTP request
     - On 2xx/4xx: Remove from queue
     - On 5xx/Timeout: Halt sync & retry later
```

### 3.1 Conflict Policies
1. **Chat Messages & Posts:** Append-only. There are no conflicts; they are processed sequentially in order of creation.
2. **Reactions (Likes):** Toggle reconciliation. If a user likes offline, and another client unlikes online, the operations are serialized. If the net state is different, the last event sync wins.
3. **Profile Edits:** Last-Write-Wins (LWW). Profile edits store a client-side timestamp. If a conflict occurs, the record with the newer timestamp overrides the old value.

---

## 4. Failure Mode Fallback Matrix

| Failure Mode | Frontend Fallback | Backend Action |
| --- | --- | --- |
| **Server Offline** | Show degraded toast; queue all writes to IndexedDB outbox. | N/A |
| **Websocket Disconnected** | Fallback to HTTP polling for notifications; buffer chat sends locally. | Drop connection from manager; publish offline presence state. |
| **Redis Down** | Fallback to local in-memory WebSocket routing (single instance degrades gracefully). | Log Redis unavailable health metric; route traffic locally. |
| **Auth Service Down** | Use local session token cache; allow read-only viewing of cached data. | Allow Supabase fallback verification. |
