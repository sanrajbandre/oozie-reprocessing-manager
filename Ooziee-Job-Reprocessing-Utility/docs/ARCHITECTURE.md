# Architecture

## Runtime topology
- `nginx` serves frontend static assets and proxies `/api` + `/ws`.
- `backend` (FastAPI + gunicorn workers) provides REST, auth, RBAC, websocket endpoint.
- `worker` polls runnable plans and executes Oozie rerun tasks with per-plan concurrency.
- `redis` carries event fanout so websocket updates work across multiple API processes.
- `mysql 8.x` (or mariadb-compatible server) stores users, plans, and task execution state.

## Execution flow
1. Admin creates plan and tasks in API.
2. Plan status changes to `RUNNING`.
3. Worker claims `PENDING` tasks and marks them `RUNNING` atomically.
4. Worker executes rerun via REST (workflow) or CLI, captures stdout/stderr/exit code.
5. Worker marks task terminal status and publishes events to Redis.
6. API consumes Redis events and broadcasts to websocket clients.

## Security model
- JWT bearer token auth.
- RBAC roles: `admin`, `viewer`.
- Bootstrap admin creation is opt-in (`BOOTSTRAP_ADMIN_ENABLED=true`).
- Production startup can enforce secret checks (`ENFORCE_SECURE_DEFAULTS=true`).
- systemd units run as dedicated non-root user (`ooziemgr`).

## Operational controls
- Liveness endpoint: `/health`
- Readiness endpoint: `/ready` (DB + Redis)
- Worker controls:
  - `WORKER_MAX_THREADS`
  - `WORKER_POLL_SECONDS`
  - `TASK_TIMEOUT_SECONDS`
  - `REST_FALLBACK_TO_CLI`

## Known constraints
- Schema migrations are currently SQL-file based (`scripts/mysql_schema.sql`).
- Running tasks cannot be force-killed through API today; cancel works for non-running tasks.
