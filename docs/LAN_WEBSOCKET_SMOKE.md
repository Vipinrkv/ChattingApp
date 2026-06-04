# LAN/WebSocket Smoke Test

`backend/tools/lan_websocket_smoke.py` validates a running backend over the same HTTP and WebSocket paths used by LAN clients.

## Automated run

Start the backend, then provide two Firebase ID tokens for test users:

```powershell
$env:SMOKE_BASE_URL="http://192.168.1.25:8000"
$env:SMOKE_USER_A_TOKEN="<firebase-id-token-a>"
$env:SMOKE_USER_B_TOKEN="<firebase-id-token-b>"
backend\venv\Scripts\python.exe backend\tools\lan_websocket_smoke.py
```

Optional overrides:

- `SMOKE_USER_A_USERNAME`, `SMOKE_USER_B_USERNAME`
- `SMOKE_USER_A_EMAIL`, `SMOKE_USER_B_EMAIL`
- `SMOKE_TIMEOUT_SECONDS`

The full smoke covers:

- `/health` and `/health/details`
- Firebase auth through user registration or `/api/v1/users/me`
- Feed post creation and personalized feed read
- Direct chat HTTP send plus WebSocket receive
- Direct chat reconnect sync and offline recovery
- Group creation, join, HTTP send, WebSocket receive, reconnect sync, and offline recovery
- Media upload through the direct chat upload endpoint

Expected result:

- The command exits with code `0`.
- Output includes `Full LAN/WebSocket smoke passed.`
- The printed user IDs are the backend UUIDs used for the direct chat, group chat, feed, and upload checks.

Use a LAN address in `SMOKE_BASE_URL` when validating another device. Use `http://127.0.0.1:8000` only for same-machine checks.

## CI guard

CI runs the script in guard mode:

```powershell
backend\venv\Scripts\python.exe backend\tools\lan_websocket_smoke.py --ci-guard
```

Guard mode does not need Firebase, a database, or a running backend. It verifies that the script imports and that this manual fallback document remains present.
It also checks that the script still contains the expected health, auth, feed, direct WebSocket chat, group WebSocket chat, reconnect/offline recovery, and media upload coverage paths.

## Two-replica Redis fanout validation

After starting two backend replicas against the same Redis instance, run the dedicated fanout validator with two Firebase-authenticated users and a group where both users are members:

```powershell
backend\venv\Scripts\python.exe backend\tools\validate_websocket_redis_fanout.py `
  --replica-a "http://127.0.0.1:8001" `
  --replica-b "http://127.0.0.1:8002" `
  --user-a-id "<database-uuid-a>" `
  --user-b-id "<database-uuid-b>" `
  --group-id "<group-uuid-with-both-users>" `
  --user-a-token "<firebase-id-token-a>" `
  --user-b-token "<firebase-id-token-b>"
```

The validator connects user A to replica A and user B to replica B, then verifies:

- Direct message delivery from replica A to replica B through Redis pub/sub.
- Group message delivery from replica A to replica B through Redis pub/sub.
- Direct chat reconnect sync after the receiver reconnects to the opposite replica.
- Group chat reconnect sync after the receiver reconnects to the opposite replica.

Expected result:

- The command exits with code `0`.
- Output includes `fanout validation passed`.
- The JSON evidence includes `replica_a_user`, `replica_b_user`, `group_id`, `direct_message_marker`, `group_message_marker`, `direct_reconnect_marker`, and `group_reconnect_marker`.

Record the JSON output in release notes or the validation evidence section of the deployment ticket. Do not mark live fanout complete from CI guard alone; this check requires real replicas, Redis, Firebase tokens, and database users.

## Manual fallback

Use this checklist when Firebase tokens are not available or a LAN device cannot run the automated smoke:

- Open `SMOKE_BASE_URL/health` from the host and one LAN device.
- Open `SMOKE_BASE_URL/health/details` and confirm the status is `ok` or `degraded` with understandable component state.
- Log in as two separate users in two browser profiles or devices.
- Create a feed post and confirm it appears after refresh.
- Open direct chat between the two users and confirm messages arrive without refresh.
- Create a public group, join from the second user, and confirm group messages arrive without refresh.
- Upload a small text or image file in direct chat and confirm the returned `/uploads/...` link opens.
- Close one chat tab, send a message while it is offline, reopen it, and confirm the missed message appears.
- Restart the backend, leave the frontend open, then confirm WebSocket chat resumes after reconnect.
- If two replicas are available, run `backend/tools/validate_websocket_redis_fanout.py` and attach its JSON output.

Record the base URL, two test user emails, pass/fail result, and any degraded `/health/details` component in the release or incident notes. If the automated smoke fails but the manual fallback passes, keep the release blocked until the failed scripted step is understood or explicitly waived by the backend owner.
