# Deployment and DevOps

## 1. Purpose

This document outlines the deployment architecture, operational workflow, and DevOps requirements for ChattingApp.

## 2. Architecture Summary

The platform is designed for containerized deployment. Local development uses Docker Compose. Production deployment is intended to use built containers, a reverse proxy, managed PostgreSQL, and Redis. GitHub Actions builds and pushes container images.

## 3. Deployment Components

- Backend: `backend/Dockerfile`
- Frontend: `frontend/Dockerfile`
- Nginx: `nginx/Dockerfile` and `nginx/default.conf`
- Local stack: `docker-compose.yml`
- CI/CD: `.github/workflows/ci-cd.yml`
- Monitoring: `prometheus/prometheus.yml`

## 4. Local Deployment

```powershell
docker compose up --build
```

Ensure the following services are available:

- backend
- frontend
- nginx
- postgres
- redis
- prometheus

For LAN and multi-device testing, use [Stable system, network access, hosting, and app conversion guide](STABILITY_HOSTING_APP_GUIDE.md). It covers host binding, CORS, allowed hosts, firewall ports, nginx WebSocket forwarding, and validation steps.

## 5. CI/CD Workflow

### Lint

- Frontend lint via `npm run lint`
- Backend lint via `flake8`

### Test

- Backend tests via `pytest`
- Services use PostgreSQL and Redis containers in CI

### Deploy

- Staging builds on `staging`
- Production builds on `main`
- Docker images are pushed to Docker Hub using secrets

### Rollback

- Rollback is handled by the workflow-dispatch rollback path using previous known-good backend and frontend image inputs.
- Follow [Production rollback runbook](PRODUCTION_ROLLBACK_RUNBOOK.md) for stop conditions, validation, and incident notes.

## 6. Production Deployment Checklist

- [ ] Build backend and frontend images successfully
- [ ] Publish images for staging and production
- [ ] Configure staging and production secrets
- [ ] Validate network and proxy rules in staging
- [ ] Validate health checks and metrics scraping
- [ ] Confirm deployment permissions and access controls
- [ ] Run database backup before migrations
- [ ] Confirm WebSocket fanout through Redis when multiple backend replicas are enabled
- [ ] Validate rollback inputs and previous known-good image references

## 7. Runtime Operations

### Health Checks

- `/health` endpoint for service readiness
- Container orchestration should restart on failure

### Secrets Management

- Use environment variables or secret store
- Do not commit `.env` files
- Strong keys required for `JWT_SECRET_KEY`, `AES_KEY`, `FIREBASE_CREDENTIALS_PATH`

### Database Migrations

- Use `python backend/tools/db_backup_and_migrate.py --database-url "$DATABASE_URL" --backup-dir "./backups"` to create a safe backup and apply Alembic migrations.
- Existing wrapper scripts in `backend/tools` can also be used for shell and PowerShell hosts.
- Migrations should be tested in staging before production

## 8. Observability and Alerts

- Scrape backend metrics with Prometheus
- Add Grafana dashboards for API, WebSocket, Redis, and DB health
- Add alerts for high error rates, backend latency, and Redis usage

## 9. Future DevOps Enhancements

- Blue-green deployment support
- Canary deployments for backend releases
- Autoscaling for backend and Redis components
- Kubernetes readiness and manifest generation
- Deployment smoke tests and rollback validation

## 10. Hosting and App Conversion

The hosting and app conversion plan is maintained in [Stable system, network access, hosting, and app conversion guide](STABILITY_HOSTING_APP_GUIDE.md). Use it for:

- Staging/production environment variables
- Managed PostgreSQL and Redis rollout
- TLS, DNS, CORS, and allowed host configuration
- PWA install verification
- Trusted Web Activity or Capacitor native shell planning

## 11. Horizontal Scaling

- API tier: run stateless FastAPI replicas behind Nginx or a cloud load balancer.
- Realtime tier: use Redis pub/sub fanout so direct and group WebSocket messages reach users connected to different replicas.
- Worker tier: split notification, moderation, media, analytics, and event-consumer jobs as queue volume grows.
- Event tier: use Redis event bus locally and Kafka when `KAFKA_BOOTSTRAP_SERVERS` is configured.
- Data tier: keep PostgreSQL primary for writes, use `READ_REPLICA_DATABASE_URL` for read scaling, and use `DB_FAILOVER_URL` for failover validation.
- Guardrails: keep jobs idempotent, include event IDs in payloads, monitor queue depth, Redis health, DB pool saturation, Kafka lag, WebSocket active connections, and `/performance`.
