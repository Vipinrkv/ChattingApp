# Local-First Architecture Strategy

This strategy document details how ChattingApp implements local-first data integrity, offline functionality, security protection, and database backups.

---

## 1. Encrypted Local Storage

To ensure user privacy, particularly when the application is running in browser sandboxes or Capacitor mobile wrappers, sensitive user data is encrypted at rest on the client side.

### 1.1 Web Crypto API & AES-GCM
- **Key Derivation:** The client derives a 256-bit symmetric encryption key from the user's master passphrase (or Firebase Auth credentials) using **PBKDF2** with a unique salt (minimum 100,000 iterations of SHA-256).
- **Encryption Algorithm:** All messages, user profile settings, and conversation histories are encrypted using **AES-256-GCM** (Galois/Counter Mode).
- **IV Requirements:** Every encryption operation generates a unique, cryptographically secure 96-bit Initialization Vector (IV). The ciphertext, the 128-bit authentication tag, and the IV are stored together in the local database.

### 1.2 Data Store Mapping (IndexedDB)
The client maintains a local database using IndexedDB (wrapped by a lightweight library like Dexie.js or localForage):
- **`messages_encrypted`:** Stores message blocks indexed by `conversation_id` and `timestamp`. The `content` column contains AES-GCM encrypted payload data.
- **`user_profile_cache`:** Caches the logged-in user's profile and privacy configurations in encrypted JSON blobs.
- **`friends_index`:** Stores the user's friend graph, public keys, and nicknames.

---

## 2. Offline Availability & Sync Queue

When network connectivity is lost (detected by the client browser via `navigator.onLine` or via failure of periodic ping requests), the client continues to function in a degraded "local-only" mode.

### 2.1 The Outbox Pattern
- All write mutations (sending messages, liking posts, changing settings) are written to a local queue called the `offline_outbox`.
- Items in the outbox are assigned a chronological sequence ID and a state: `pending`, `syncing`, or `failed`.
- The user is notified via a subtle reconnect banner (`ReconnectBanner.tsx`), and the local UI displays optimistic updates (e.g. showing the message with a "pending clock" icon).

### 2.2 Client-Side Generated UUIDs & Idempotency
To prevent message duplication during network retries:
1. Every message or post created offline is immediately stamped with a client-generated **UUIDv4**.
2. When connection is restored, the client posts these items to the backend.
3. The backend database schema contains unique constraints on `client_uuid`. If a duplicate uuid is received (e.g., from a timed-out request that actually succeeded on the server), the backend ignores the duplicate write and returns `200 OK` with the existing resource.

### 2.3 Conflict Resolution Protocol
1. **Append-Only Threads:** For message logs and social feed comment threads, order is determined by chronological timestamp. In case of tie-breakers, client UUIDs are sorted lexicographically.
2. **Last-Write-Wins (LWW):** For settings modifications and profile edits, the client includes a high-resolution timestamp. The backend overwrites records only if the incoming timestamp is newer than the database's `updated_at` timestamp.
3. **Optimistic UI Merges:** Feeds optimism merges locally. If a post is liked offline, the client increments the visual counter immediately. The sync engine processes this sequentially.

---

## 3. Media Sync & Integrity Validation

Offline media handling requires extra verification to ensure consistency and prevent unauthorized binary execution.

### 3.1 Content Integrity Verification
- **SHA-256 Hashing:** Before any media upload is queued or transmitted, the client computes a **SHA-256 checksum** of the binary file block.
- **Deduplication:** The backend queries the database for the file hash before accepting the payload. If the hash already exists, the server maps the new message to the existing media record instead of saving a duplicate file.
- **Signatures:** Uploaded media undergoes magic-byte inspections (validating file header structures against claimed file extensions) to prevent executable uploads.

### 3.2 Offline Media Cache
- Large media files are cached in the browser's Cache Storage API via service workers.
- When offline, images and video previews are loaded from Cache Storage using their SHA-256 hash or CDN URL as keys.

---

## 4. Encrypted Backups & Restore Validation

Users can export their entire chat history securely.

### 4.1 Server-Triggered Backup Workflow
1. The client requests a backup archive.
2. The backend generates a JSON export of all chats and messages, encrypts it using an ephemeral key or the user's derived key, and uploads the backup archive to object storage (S3/MinIO).
3. The database logs the backup metadata (file path, SHA-256 hash, backup date, total messages, owner ID) in the `backups` table.

### 4.2 Restore Validation Pipeline
1. During restoration, the client downloads the archive.
2. The client calculates the file's SHA-256 hash and compares it against the database metadata block to guarantee that the file was not altered in transit.
3. The client decrypts the payload locally. If the authentication tag fails (indicating tampering or incorrect passphrase), the restore operation is aborted, and a security audit alert is emitted.
