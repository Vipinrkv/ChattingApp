# Documentation Index

This directory contains architecture, operations, onboarding, and planning documents for ChattingApp.

## How to use this folder

- Read `docs/README.md` first for a consolidated entry point.
- Use [Development guide](DEVELOPMENT_GUIDE.md) for onboarding, local setup, engineering rules, sprint discipline, and release practices.
- Use [WorkProgress](../WorkProgress.md) for active status and current priorities.
- Use [System audit and architecture plan](SYSTEM_AUDIT_AND_ARCHITECTURE_PLAN.md) for the cleanup and architecture roadmap.
- Use [Stable system, network access, hosting, and app conversion guide](STABILITY_HOSTING_APP_GUIDE.md) for LAN access, multi-connection validation, hosting, and PWA/native app conversion planning.
- Use [Local-first multi-user stability plan](LOCAL_FIRST_MULTI_USER_STABILITY_PLAN.md) for encrypted local storage, backup/restore, feed event-chain integrity, settings, LAN, and online rollout planning.
- Keep this file updated whenever you add, archive, rename, or reorganize docs.

## Document categories

### Project tracking and planning

- [System audit and architecture plan](SYSTEM_AUDIT_AND_ARCHITECTURE_PLAN.md) - cleanup roadmap for error handling, fallback behavior, admin panel work, file organization, and documentation consolidation
- [Stable system, network access, hosting, and app conversion guide](STABILITY_HOSTING_APP_GUIDE.md) - stability plan for local/LAN multi-connection usage, hosting rollout, and app conversion
- [Local-first multi-user stability plan](LOCAL_FIRST_MULTI_USER_STABILITY_PLAN.md) - encrypted local-first data, backup/restore, settings, feed event-chain integrity, LAN, and online rollout roadmap
- [WorkProgress](../WorkProgress.md) - current engineering roadmap and active task list
- [Development guide](DEVELOPMENT_GUIDE.md) - onboarding, local setup, engineering rules, sprint discipline, and release practices

### Architecture and system design

- [System audit and architecture plan](SYSTEM_AUDIT_AND_ARCHITECTURE_PLAN.md)
- [Database and backend details](DATABASE_BACKEND_DETAILS.md)
- [Connection structure](CONNECTION_STRUCTURE.md)
- [File structure and system flow](FILE_STRUCTURE_AND_SYSTEM_FLOW.md)
- [Realtime architecture](REALTIME_ARCHITECTURE.md)
- [Stable system, network access, hosting, and app conversion guide](STABILITY_HOSTING_APP_GUIDE.md)
- [Local-first multi-user stability plan](LOCAL_FIRST_MULTI_USER_STABILITY_PLAN.md)
- [Security architecture](SECURITY_ARCHITECTURE.md)
- [Multi-tenant architecture](MULTI_TENANT_ARCHITECTURE.md)
- [AI moderation and safety](AI_MODERATION_AND_SAFETY.md)
- [Mohalla Connect architecture](MOHALLA_CONNECT_ARCHITECTURE.md)
- [Mohalla Connect implementation plan](MOHALLA_CONNECT_IMPLEMENTATION_PLAN.md)

### Operations and deployment

- [Deployment and DevOps](DEPLOYMENT_AND_DEVOPS.md)
- [Stable system, network access, hosting, and app conversion guide](STABILITY_HOSTING_APP_GUIDE.md)
- [Development guide](DEVELOPMENT_GUIDE.md)
- [Observability](OBSERVABILITY.md)
- [Alembic production](ALEMBIC_PRODUCTION.md)
- [Production rollback runbook](PRODUCTION_ROLLBACK_RUNBOOK.md)

### Safety and moderation

- [AI moderation and safety](AI_MODERATION_AND_SAFETY.md)

## Maintenance

- Keep current status in one place: `WorkProgress.md` for progress tracking and `SYSTEM_AUDIT_AND_ARCHITECTURE_PLAN.md` for cleanup/architecture planning.
- Merge stale docs instead of duplicating completion percentages across multiple files.
- Use relative links so the docs folder remains portable.
- Every current doc should have a clear purpose: overview, architecture, runbook, roadmap, or historical note.
