# Feature Ticket List — ChattingApp

This Feature Ticket List contains standard engineering task tickets mapping to critical parts of the **ChattingApp** platform. Each ticket is designed to be a standalone, actionable task description with clear acceptance criteria and dependencies.

---

## Ticket 1: User Feed Settings Configuration Panel

- **Feature Name**: User Feed Settings Panel
- **Task Description**: Implement a "Feed Settings" modal in the React frontend page (`Feed.tsx`) that allows the user to view and update their feed preferences. The UI should connect to the `GET` and `PUT` `/api/v1/posts/controls` backend endpoints.
- **Acceptance Criteria**:
  - A settings cog icon on the Feed page triggers the modal overlay.
  - Users can input muted words (comma-separated), select ranking mode (Chronological vs Engagement), and toggle sensitive content filters.
  - Settings are saved to the backend database and persisted in the local Zustand store on save success.
  - If backend is offline, settings fall back to local IndexedDB config and queue a sync request.
- **Dependencies**: REST API endpoint router `/api/v1/posts/controls` must be registered.
- **Priority**: Must-have for launch.

---

## Ticket 2: Nested Quote Post Composer & Renderer

- **Feature Name**: Nested Quote Post Composer & Renderer
- **Task Description**: Update the social feed post creation form and feed rendering lists to support quote posts. When a post contains a `quoted_post_id`, render the target post as a nested, read-only card inside the main post card.
- **Acceptance Criteria**:
  - The "Share" button on any post has a drop-down option for "Quote Post".
  - Clicking "Quote Post" opens the post composer with a preview of the quoted post attached at the bottom.
  - Saving the post sends a payload containing the `quoted_post_id` to the `POST /api/v1/posts` endpoint.
  - The feed correctly fetches and renders the nested quoted post card, styled with a distinct border and background highlight.
- **Dependencies**: SQLAlchemy post model must support `quoted_post_id` self-referencing relationship.
- **Priority**: Must-have for launch.

---

## Ticket 3: Group Member Role Customization Dropdown

- **Feature Name**: Group Member Role Selector
- **Task Description**: Add a members listing screen inside the `Groups.tsx` component. For group owners and administrators, show a dropdown next to each member to change their role status (Admin, Moderator, Member) or kick them from the group.
- **Acceptance Criteria**:
  - Clicking on a group opens a "Members" tab listing all participants and their current roles.
  - If the active user has Owner or Admin permission, rendering includes a role selector dropdown.
  - Selecting a role triggers a `PATCH /api/v1/groups/{group_id}/members/{user_id}/role` request.
  - Non-admin members only see the members list without dropdown selectors.
- **Dependencies**: Group service `update_member_role` service logic complete.
- **Priority**: Must-have for launch.

---

## Ticket 4: Encrypted Backup & Restore Wizard

- **Feature Name**: Encrypted Backup & Restore Wizard
- **Task Description**: Build a Settings panel wizard for user data backups. The wizard should allow users to trigger a manual backup (entering a passphrase to encrypt chat history with AES-GCM) or upload a backup file to restore their local client messages and IndexedDB drafts.
- **Acceptance Criteria**:
  - Users can select "Export Encrypted Backup". Inputting a passphrase generates a base64url-encoded AES key, runs the encryption client-side, and downloads a backup package.
  - Users can select "Import Backup". Uploading the package and entering the correct passphrase decrypts the archive, validates the manifest file, and imports data into IndexedDB.
  - Tampered or corrupted backup archives throw a visible warning and block the import process.
- **Dependencies**: Web Crypto API libraries available.
- **Priority**: Must-have for launch.

---

## Ticket 5: Media Transcoding & Signature Pipelines

- **Feature Name**: Media Validation and Transcoding Pipeline
- **Task Description**: Implement validation and compression logic inside the media upload service (`media_service.py`) to convert images to WebP format, transcode audio recordings to MP3 format, and validate file signatures to block malicious uploads.
- **Acceptance Criteria**:
  - Uploaded JPG/PNG images are automatically converted to WebP with PIL compression.
  - Uploaded audio voice notes are transcoded to MP3 using FFmpeg (with a graceful raw file fallback if FFmpeg is missing).
  - Validation steps parse file headers to match magic numbers against expected mime types.
- **Dependencies**: PIL and FFmpeg binaries accessible in execution environment.
- **Priority**: Must-have for launch.

---

## Ticket 6: Automated Markdown Link Checker CI Script

- **Feature Name**: Automated Markdown Link Validator
- **Task Description**: Add a Python script `check_markdown_links.py` under the tools directory that parses all `.md` files in the repository and verifies that all relative and absolute local paths (`file:///`) are correct. Integrate this script as a lint step in the GitHub Actions configuration.
- **Acceptance Criteria**:
  - Running the script scans all markdown files in the repository.
  - Directory traversal skips `node_modules` and `.git` folders for optimal execution speeds.
  - The script returns exit code `1` if any broken links are detected and `0` otherwise.
  - The CI workflow runner halts the build on failure.
- **Dependencies**: Python standard libraries only.
- **Priority**: Should-have for deployment.

---

## Ticket 7: Distributed WebSocket Instance Synchronization

- **Feature Name**: Redis WebSocket Pub/Sub Fanout
- **Task Description**: Configure the WebSocket broker class (`redis_broker.py`) to run Redis pub/sub channels. When a user sends a message, publish it to a global Redis channel so that all connected backend replica instances receive and broadcast it to target connected sockets.
- **Acceptance Criteria**:
  - Multi-instance local compose setups successfully broadcast message events.
  - If a user changes their online status, the status event syncs across all instances.
  - If Redis is disconnected, the WebSocket manager falls back gracefully to in-process delivery.
- **Dependencies**: Redis instance running.
- **Priority**: Must-have for production scaling.

---

## Ticket 8: Automated End-to-End System Smoke Test

- **Feature Name**: System Deployment Smoke Test
- **Task Description**: Write a system-level integration script `deployment_smoke_test.py` that registers test users, publishes posts, sends direct/group messages, uploads attachments, and runs a security backup export to verify system sanity.
- **Acceptance Criteria**:
  - The script accepts an target host URL via environment variable (`SMOKE_TEST_HOST`).
  - Executes registration, authorization, feed creation, DM messaging, and admin overview calls.
  - Returns exit code `0` on success.
- **Dependencies**: FastAPI server running.
- **Priority**: Should-have for deployment stability.

---

## Ticket 9: Capacitor wrapped Android native build

- **Feature Name**: Capacitor Android wrapper build
- **Task Description**: Configure Capacitor wrapper tools, initialize the Android workspace platform under `frontend/android/`, sync production React assets, and assemble the release APK.
- **Acceptance Criteria**:
  - Running `npx cap sync android` successfully syncs web assets.
  - Opening the native project in Android Studio builds a runnable release package.
- **Dependencies**: Android SDK configured.
- **Priority**: Must-have for mobile launch.

---

## Ticket 10: TAMPER-EVIDENT EVENT CHAIN

- **Feature Name**: Feed Event Integrity Chain
- **Task Description**: Implement a tamper-evident event logging system `feed_event_chain_service.py` that computes SHA-256 hashes for all feed interactions, linking each log event block to the previous entry hash.
- **Acceptance Criteria**:
  - Event creation generates a chain hash.
  - The verification function auditing the database returns `false` if any row is tampered or deleted.
- **Dependencies**: SQLAlchemy migration complete.
- **Priority**: Should-have.

---

## 11. Embedded Feature Ticket List Prompt
To generate or iterate on this Feature Ticket List, use the following prompt:
> "Act as a senior engineering lead who breaks down products into buildable tasks. Based on my PRD and Technical Architecture, create a complete Feature Ticket List for my app. For each feature, write a ticket that includes the feature name, a clear description of what needs to be built, acceptance criteria that defines when the task is done, any dependencies on other features that must be completed first, and a priority label — must-have for launch, should-have, or nice-to-have. Write each ticket so it can be directly used as a prompt for an AI coding tool. The target application is a secure real-time chatting and social feed platform featuring Firebase authentication, PostgreSQL database connections, Redis pub/sub broker synchronizations, S3/Local storage adapters, Web Crypto AES-GCM local backups, and Capacitor Android mobile wrapper builds."
