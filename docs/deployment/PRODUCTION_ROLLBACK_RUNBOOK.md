# Production Rollback Runbook

This runbook keeps rollback boring: redeploy the last known-good images, verify health, and only then resume promotion.

## Preconditions

- Docker image tags are immutable for release builds.
- `PREVIOUS_BACKEND_IMAGE` and `PREVIOUS_FRONTEND_IMAGE` are recorded before production promotion.
- Database migrations follow `docs/ALEMBIC_PRODUCTION.md`; destructive migrations require a restore plan before deploy.
- Rollback operators have production environment approval in GitHub Actions.

## GitHub Actions Rollback

1. Open **CI / CD** in GitHub Actions.
2. Run workflow manually with `deploy_target=rollback`.
3. Provide:
   - `previous_backend_image`, for example `ghcr.io/org/chattingapp-backend:2026-06-04-good`
   - `previous_frontend_image`, for example `ghcr.io/org/chattingapp-frontend:2026-06-04-good`
4. Confirm the workflow writes the selected images to `rollback-manifest.txt`.
5. Use the generated manifest in the production deploy system, or wire the deploy provider to consume those image values directly.

## Manual Rollback

1. Freeze new deploys and announce rollback ownership.
2. Redeploy the previous backend image.
3. Redeploy the previous frontend image.
4. Run `/health/details`, `/metrics`, and a login/chat smoke test.
5. Run the WebSocket fanout validation if backend replicas are involved.
6. Record the incident, root cause, image tags, and validation evidence in the release log.

## Verification Commands

```powershell
venv\Scripts\python.exe tools\validate_observability_export.py --base-url https://api.example.com
venv\Scripts\python.exe tools\validate_websocket_redis_fanout.py --replica-a http://backend-a:8000 --replica-b http://backend-b:8000 --user-a-id <uuid> --user-b-id <uuid> --user-a-token <token> --user-b-token <token>
```

## Stop Conditions

- Rollback image fails `/health/details`.
- Database schema is incompatible with the previous backend image.
- Error rate or WebSocket disconnect rate continues increasing after rollback.

If any stop condition is hit, move to restore/failover using `docs/ALEMBIC_PRODUCTION.md` and keep the failed rollback manifest attached to the incident notes.
