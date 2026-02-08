# Oozie Reprocessing Manager

Enterprise-grade Oozie rerun/reprocessing manager built for production operations on Linux servers.

## What This Project Solves

Large Oozie estates often need controlled reruns across workflows, coordinators, and bundles, with traceability and role-based access.  
This project provides a full-stack control plane to create reprocessing plans, execute tasks safely, and monitor progress in real time.

## Highlights

- Multi-plan rerun orchestration with task-level execution state
- Support for workflow, coordinator, and bundle rerun patterns
- Role-based access control (admin/viewer) with JWT authentication
- Live execution updates via WebSocket + Redis Pub/Sub
- Background worker with plan-level concurrency controls
- MySQL 8.x first-class support (MariaDB compatible)
- Production-focused deployment on Rocky Linux 9.x / CentOS Stream 9

## Runtime Architecture

1. React frontend sends plan/task actions to FastAPI backend.
2. FastAPI stores state in MySQL and publishes events to Redis.
3. Worker consumes runnable tasks and executes Oozie reruns (REST/CLI).
4. API broadcasts Redis events to connected WebSocket clients.

## Repository Layout

- `Ooziee-Job-Reprocessing-Utility/frontend`: React + Vite UI
- `Ooziee-Job-Reprocessing-Utility/backend`: FastAPI API + auth + routes
- `Ooziee-Job-Reprocessing-Utility/worker`: async/background execution runner
- `Ooziee-Job-Reprocessing-Utility/deploy`: systemd, nginx, env, install scripts
- `Ooziee-Job-Reprocessing-Utility/docs`: architecture and deployment guides

## MySQL 8.x Support

Recent upgrades include:

- MySQL-aware SQLAlchemy engine tuning for API and worker
- Runtime DB URL validation (`mysql+pymysql://...?...charset=utf8mb4`)
- Startup/readiness checks for MySQL 8+ compatibility
- Installer defaults to MySQL 8 (`DB_FLAVOR=mysql8`)
- DB bootstrap script supports MySQL auth plugin selection (`caching_sha2_password` default)

## Quick Start

Main implementation and detailed setup:

- Project README: `Ooziee-Job-Reprocessing-Utility/README.md`
- Deployment guide: `Ooziee-Job-Reprocessing-Utility/docs/DEPLOYMENT.md`
- Architecture notes: `Ooziee-Job-Reprocessing-Utility/docs/ARCHITECTURE.md`

## License

Apache-2.0
