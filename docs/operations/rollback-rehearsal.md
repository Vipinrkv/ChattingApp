# Deployment Rollback Runbook & Rehearsal Plan

This document defines the protocols, triggers, and execution steps for rolling back deployments and database schema changes in the event of production instability.

## Rollback Decisions & Triggers

A rollback is initiated under the following conditions:
1. **Critical Latency Degradation**: Request duration p95 latency > `1500ms` for > 3 minutes post-deployment.
2. **Crash Loop Backoff**: Containers repeatedly crash on boot due to startup failures, unhandled environment variables, or database connection limits.
3. **Elevated Error Rates**: HTTP 5xx responses exceed `5%` of total traffic.
4. **Data Corruption**: A deployment causes incorrect writes or data inconsistency in the database.

## Step-by-Step Rollback Execution

### Step 1: Rollback Container Deployment (Zero-Downtime)

To immediately restore service, the container instances are reverted to the previous stable release tag.

#### Using Docker Compose / Local Swarm:
1. Identify the previous stable image tag in the release history.
2. Update the environment or compose configuration with the target stable version:
   ```bash
   # Revert application container to previous tag
   docker service update --image chattingapp-backend:v1.2.0 chattingapp_backend
   ```
3. Monitor container health to ensure replicas startup and successfully pass healthcheck probes.

#### Using Kubernetes (if applicable):
```bash
kubectl rollout undo deployment/chattingapp-backend
kubectl rollout status deployment/chattingapp-backend
```

---

### Step 2: Rollback Database Migrations (Alembic)

If the new deployment introduced schema migrations that must be undone, Alembic migrations must be rolled back carefully to prevent data loss.

> [!WARNING]
> Rolling back database schemas can result in loss of data written since the migration ran. Perform a database snapshot before proceeding.

1. **Access backend terminal**:
   ```bash
   cd backend
   ```
2. **Inspect migration status**:
   ```bash
   alembic history --verbose
   alembic current
   ```
3. **Downgrade to the previous revision**:
   To undo the single most recent migration:
   ```bash
   alembic downgrade -1
   ```
   To downgrade to a specific historical revision:
   ```bash
   alembic downgrade <revision_id>
   ```

---

### Step 3: Verify Post-Rollback System Health

Run the following checks to confirm the rollback was successful:
1. Run smoke test scripts:
   ```bash
   python backend/tools/deployment_smoke_test.py
   ```
2. Monitor log streams for syntax or connection errors:
   ```bash
   docker compose logs -f backend
   ```
3. Verify Prometheus/Grafana dashboard indicates active WebSocket connections are rising and HTTP 500 error counts drop back to zero.
4. Inform the engineering team of the rollback cause and status.
