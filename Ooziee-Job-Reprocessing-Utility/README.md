# oozie-reprocessing-manager

Enterprise-grade Oozie rerun / reprocessing manager.

**Stack**
- Frontend: React + Vite (TypeScript)
- Backend: FastAPI (Python 3.8+) + JWT Auth + RBAC (admin/viewer) + WebSocket live updates
- Worker: background runner (plan-level concurrency limits)
- Storage: MySQL (recommended) / SQLite (dev)
- Messaging: Redis Pub/Sub for WebSocket broadcasts (required for multi-process)

## Features
- Create and manage multiple **Reprocessing Plans**
- Add tasks for **Workflow / Coordinator / Bundle** rerun patterns
- **Start / Pause / Resume / Stop** plans
- Live **WebSocket** updates (no polling)
- **RBAC** (admin vs viewer) with JWT login
- **Plan-level concurrency** (parallel runners with limits)
- **Oozie REST integration** to fetch job status & action graph, plus CLI execution support
- Works on **CentOS 7.x** (via pyenv Python 3.8+), **Rocky 9.x**, and most Linux distributions

## Quickstart
See `docs/DEPLOYMENT.md`.

## License
Apache-2.0
