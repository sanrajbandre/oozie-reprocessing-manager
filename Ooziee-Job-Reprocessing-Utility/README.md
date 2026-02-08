# Oozie Reprocessing Manager

Production-focused Oozie rerun/reprocessing manager.

## Stack
- Frontend: React + Vite (TypeScript)
- API: FastAPI + JWT + RBAC + WebSocket
- Worker: Python background executor with plan-level concurrency
- Storage: MariaDB/MySQL (SQLite optional for local dev)
- Messaging: Redis Pub/Sub
- Deployment: systemd + nginx on Rocky Linux 9.x / CentOS Stream 9

## What is hardened in this version
- Runtime configuration validation for production secrets
- Optional schema auto-create (disabled by default)
- Optional admin bootstrap (disabled by default)
- Readiness endpoint with DB and Redis checks (`/ready`)
- Safer worker task execution (CLI arguments without `shell=True`)
- Atomic task claiming to reduce duplicate execution risk
- Task timeout and fallback controls for rerun behavior
- Hardened systemd units (non-root, tighter service sandboxing)
- Nginx production reverse proxy + static frontend config
- Deployment scripts for Rocky/CentOS 9

## Quick links
- Deployment steps: `docs/DEPLOYMENT.md`
- Env template: `deploy/env/oozie-reprocess.env.example`
- Installer script: `deploy/scripts/install-rocky9.sh`

## License
Apache-2.0
