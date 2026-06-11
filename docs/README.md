# ChattingApp Documentation Index

This directory contains the system architecture, operations runbooks, security profiles, and final audit reports for the ChattingApp platform.

---

## 📂 Reorganized Documentation Categories

### 1. 🛡️ Security & Integrity
* [Security Architecture](security/security-architecture.md) — Comprehensive security policies (MFA, session verification, refresh token rotation).
* [Event Chain Integrity](security/event-chain-integrity.md) — Immutable log auditing and blockchain-inspired SHA-256 event chaining.
* [Security Report](audit/security-report.md) — Security posture review, threat modeling, and E2EE.

### 2. 🏗️ Architecture & Real-Time Sync
* [Offline-First Architecture](architecture/offline-first.md) — Local-first IndexedDB outbox queue and conflict reconciliation.
* [Provider Management](architecture/provider-management.md) — Centralized external service abstractions and configuration interfaces.
* [Real-Time Architecture](REALTIME_ARCHITECTURE.md) — WebSocket gateway design and Redis multi-node message fanout.
* [Mohalla Connect Architecture](MOHALLA_CONNECT_ARCHITECTURE.md) — Connect module and integration.

### 3. 💾 Database Schema
* [Database Review](database/database-review.md) — Database design overview, indexing strategy, and constraints.
* [Database Backend Details](DATABASE_BACKEND_DETAILS.md) — Deep dive into entity models and relationship configurations.

### 4. 🚀 Deployment & Operations
* [Zero-Cost Production Strategy](deployment/free-production-strategy.md) — Deploying with PostgreSQL, Redis, and MinIO without cloud provider dependencies.
* [Observability Guide](operations/observability.md) — Metrics scrapers, alerting parameters, and Grafana.
* [Production Rollback Runbook](PRODUCTION_ROLLBACK_RUNBOOK.md) — Disaster recovery and rollback steps.

### 5. 📱 Mobile & PWA
* [Android PWA Conversion](ANDROID_CONVERSION.md) — Capacitor configurations.
* [Android Readiness Report](audit/android-readiness-report.md) — Mobile bridge guidelines.

---

## 📋 Compiled Audit Reports

We have compiled the 11 final engineering reports detailing the production readiness of the ChattingApp platform:

1. [Production Readiness Report](audit/production-readiness-report.md) — Executive summary of security, offline reliability, and database states.
2. [Security Report](audit/security-report.md) — Multi-tier authentication fallbacks, device binding, and token rotation.
3. [Android Readiness Report](audit/android-readiness-report.md) — WebManifest properties, service workers, and native mobile roadmap.
4. [Scalability Report](audit/scalability-report.md) — Horizontal scaling models for WebSockets and sharding plans from 1K to 1M users.
5. [Observability Report](audit/observability-report.md) — Prometheus indicators and alerting parameters.
6. [Admin Panel Report](audit/admin-panel-report.md) — Access rules and operational dashboard specifications.
7. [Monetization Report](audit/monetization-report.md) — Native ad placements, targeted rules, and campaign database schemas.
8. [Documentation Cleanup Report](audit/documentation-cleanup-report.md) — Reorganization index for markdown resources.
9. [System Validation Report](testing/system-validation-report.md) — Validation procedures for authentication, load, reliability, and offline sync.
10. [Remaining Risks Report](audit/remaining-risks-report.md) — coturn TURN relays, media pruners, and geolocation dependencies.
11. [Updated WorkProgress](../WORKPROGRESS.md) — Priority ratings and estimated efforts for remaining tasks.

---

## 🛠️ Onboarding and Development

* [Development Guide](DEVELOPMENT_GUIDE.md) — Local setup, linting rules, running test suites, and git branching models.
