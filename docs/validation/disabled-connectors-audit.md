# Google Cloud Connectors Audit & Disabling

This document records the audit and disabling of unused Google Cloud data connectors in the ChattingApp project to optimize performance and prevent unnecessary resource loading.

## 1. Audit Scope & Discovery
During the system audit, we inspected all enabled MCP servers, remote tools, and data connectors. We identified that the following Google Cloud connectors were configured as part of the MCP environment in `C:\Users\Vipin\.gemini\config\mcp_config.json`:

- `datacloud_alloydb_remote` (AlloyDB remote server)
- `datacloud_bigquery_remote` (BigQuery remote server)
- `datacloud_cloud-sql_remote` (Cloud SQL remote server)
- `datacloud_dataproc_remote` (Dataproc remote server)
- `datacloud_knowledge_catalog_remote` (Dataplex remote server)
- `datacloud_spanner_remote` (Spanner remote server)

## 2. Usage Assessment
The ChattingApp project uses:
- **Database**: PostgreSQL (Supabase / local Docker instance) and SQLite (for tests).
- **Cache & Realtime**: Redis (local / hosted).
- **Auth**: Firebase Admin (backend) and Firebase Client SDK (frontend).
- **Storage**: Local filesystem uploads with fallback support for S3/CDN.

None of the Google Cloud connectors listed above are used by the application backend, frontend, or testing suites.

## 3. Disabling & Cleanup Action
To optimize the development environment, reduce memory usage, and prevent these unused remote connectors from loading:
1. **Config Cleanup**: Removed all 6 `datacloud_*` remote server definitions from the active configuration file: [mcp_config.json](file:///C:/Users/Vipin/.gemini/config/mcp_config.json). Only `notebooks` and `visualization` remain active.
2. **Startup Registrations**: Verified that no backend code (`main.py`, database `connection.py`, Celery/RQ workers) or frontend code registers or depends on these Google Cloud connectors.
3. **Environment Variables**: Verified that no environment variables or settings in `.env`, `.env.production`, or active shell processes are present for these services.
4. **Local Development Integration**: Checked all local development startup routines (`package.json`, `docker-compose.yml`, local test runners) to confirm no automatic loading of GCP connectors is configured.

## 4. Verification
- All 30 tests in the test suite run successfully and pass.
- Disabling the connectors has no impact on existing production or development functionality, keeping the environment clean and focused.
