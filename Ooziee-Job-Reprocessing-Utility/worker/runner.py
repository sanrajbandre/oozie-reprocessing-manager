import json
import logging
import os
import shlex
import signal
import socket
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from threading import Event
from typing import Dict, List, Set, Tuple

import redis
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
from app.db import build_engine  # type: ignore
from app.models import Plan, Task  # type: ignore
from app.oozie import OozieClient  # type: ignore
from app.settings import Settings  # type: ignore

settings = Settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s [worker] %(message)s",
)
logger = logging.getLogger(__name__)

ENGINE = build_engine(settings.db_url)
SessionLocal = sessionmaker(bind=ENGINE, autocommit=False, autoflush=False)

REDIS = redis.from_url(settings.redis_url, decode_responses=True)

OOZIE_BIN = os.environ.get("OOZIE_BIN", "oozie")
PRE_TASK_CMD = os.environ.get("PRE_TASK_CMD", "").strip()
PRE_TASK_SHELL_CMD = os.environ.get("PRE_TASK_SHELL_CMD", "").strip()

POLL_SECONDS = int(os.environ.get("WORKER_POLL_SECONDS", "3"))
WORKER_MAX_THREADS = int(os.environ.get("WORKER_MAX_THREADS", "32"))
TASK_TIMEOUT_SECONDS = int(os.environ.get("TASK_TIMEOUT_SECONDS", "1800"))
MAX_STDOUT = int(os.environ.get("MAX_STDOUT", "50000"))
MAX_STDERR = int(os.environ.get("MAX_STDERR", "50000"))
REST_FALLBACK_TO_CLI = os.environ.get("REST_FALLBACK_TO_CLI", "true").strip().lower() in {"1", "true", "yes"}

WORKER_ID = os.environ.get("WORKER_ID", f"{socket.gethostname()}-{os.getpid()}")
SHUTDOWN = Event()


def publish(event: dict) -> None:
    try:
        REDIS.publish(settings.redis_channel, json.dumps(event, default=str))
    except Exception as exc:
        logger.warning("event publish failed: %s", exc.__class__.__name__)


def now() -> datetime:
    return datetime.utcnow()


def _trim(value: str, max_size: int) -> str:
    return (value or "")[:max_size]


def _fmt_command(parts: List[str]) -> str:
    return shlex.join(parts)


def build_cli_command(plan: Plan, task: Task) -> List[str]:
    oozie_url = (plan.oozie_url or settings.oozie_default_url).strip()
    if not oozie_url:
        raise RuntimeError("oozie_url not configured")

    cmd: List[str] = [OOZIE_BIN, "job", "-oozie", oozie_url, "-rerun", task.job_id]

    if task.type == "workflow":
        props = {}
        if task.wf_skip_nodes:
            props["oozie.wf.rerun.skip.nodes"] = task.wf_skip_nodes
        else:
            props["oozie.wf.rerun.failnodes"] = "true" if task.wf_failnodes else "false"

        if task.extra_props:
            for k, v in (task.extra_props or {}).items():
                props[str(k)] = str(v)

        for k, v in props.items():
            cmd.append(f"-D{k}={v}")
        cmd.append("-nocleanup")

    elif task.type == "coordinator":
        if task.action:
            cmd.extend(["-action", task.action])
        elif task.date:
            cmd.extend(["-date", task.date])
        else:
            raise RuntimeError("coordinator rerun requires action or date")

        if task.failed:
            cmd.append("-failed")
        if task.refresh:
            cmd.append("-refresh")
        cmd.append("-nocleanup")

    elif task.type == "bundle":
        if task.coordinator:
            cmd.extend(["-coordinator", task.coordinator])
        elif task.date:
            cmd.extend(["-date", task.date])
        else:
            raise RuntimeError("bundle rerun requires coordinator or date")

        if task.refresh:
            cmd.append("-refresh")
        cmd.append("-nocleanup")
    else:
        raise RuntimeError("unknown task type")

    return cmd


def _run_pre_task_hook() -> Tuple[int, str, str]:
    if PRE_TASK_CMD:
        cmd = shlex.split(PRE_TASK_CMD)
        pre = subprocess.run(cmd, text=True, capture_output=True, timeout=TASK_TIMEOUT_SECONDS)
        return pre.returncode, _trim(pre.stdout or "", MAX_STDOUT), _trim(pre.stderr or "", MAX_STDERR)

    if PRE_TASK_SHELL_CMD:
        logger.warning("PRE_TASK_SHELL_CMD is deprecated and less secure. Prefer PRE_TASK_CMD.")
        pre = subprocess.run(PRE_TASK_SHELL_CMD, shell=True, text=True, capture_output=True, timeout=TASK_TIMEOUT_SECONDS)
        return pre.returncode, _trim(pre.stdout or "", MAX_STDOUT), _trim(pre.stderr or "", MAX_STDERR)

    return 0, "", ""


def _workflow_rest_rerun(plan: Plan, task: Task) -> Tuple[str, str, str, int]:
    if task.type != "workflow":
        raise RuntimeError("REST rerun is supported for workflow tasks only")

    oozie_url = (plan.oozie_url or settings.oozie_default_url).strip()
    if not oozie_url:
        raise RuntimeError("oozie_url not configured")

    conf = {}
    if task.wf_skip_nodes:
        conf["oozie.wf.rerun.skip.nodes"] = task.wf_skip_nodes
    else:
        conf["oozie.wf.rerun.failnodes"] = "true" if task.wf_failnodes else "false"

    for k, v in (task.extra_props or {}).items():
        conf[str(k)] = str(v)

    client = OozieClient(oozie_url)
    response = client.rerun(task.job_id, conf=conf if conf else None, params=None)
    command = f"REST PUT {client.base_url}/v2/job/{task.job_id}?action=rerun"
    return command, json.dumps(response, default=str), "", 0


def _mark_task_result(task: Task, command: str, stdout: str, stderr: str, exit_code: int) -> None:
    task.command = command
    task.stdout = _trim(stdout, MAX_STDOUT)
    task.stderr = _trim(stderr, MAX_STDERR)
    task.exit_code = exit_code
    task.ended_at = now()
    task.status = "SUCCESS" if exit_code == 0 else "FAILED"


def _claim_task(db, task: Task) -> bool:
    claimed = (
        db.query(Task)
        .filter(Task.id == task.id, Task.status == "PENDING")
        .update(
            {
                Task.status: "RUNNING",
                Task.started_at: now(),
                Task.attempt: Task.attempt + 1,
            },
            synchronize_session=False,
        )
    )
    if claimed != 1:
        db.rollback()
        return False
    db.commit()
    db.refresh(task)
    return True


def run_task(plan_id: int, task_id: int) -> None:
    db = SessionLocal()
    try:
        plan = db.get(Plan, plan_id)
        task = db.get(Task, task_id)
        if not plan or not task:
            return
        if plan.status != "RUNNING":
            return
        if not _claim_task(db, task):
            return

        publish({"event": "task_started", "plan_id": plan_id, "task_id": task_id, "worker_id": WORKER_ID})

        hook_code, hook_out, hook_err = _run_pre_task_hook()
        if hook_code != 0:
            _mark_task_result(task, "PRE_TASK_CMD", hook_out, hook_err, hook_code)
            db.commit()
            publish({"event": "task_finished", "plan_id": plan_id, "task_id": task_id, "status": task.status, "worker_id": WORKER_ID})
            return

        cmd_text = ""
        out = ""
        err = ""
        exit_code = 1

        if plan.use_rest:
            try:
                cmd_text, out, err, exit_code = _workflow_rest_rerun(plan, task)
            except Exception as exc:
                if not REST_FALLBACK_TO_CLI:
                    raise
                err = f"REST rerun failed ({exc.__class__.__name__}): {exc}\nFalling back to CLI rerun."

        if cmd_text == "":
            cli_cmd = build_cli_command(plan, task)
            cmd_text = _fmt_command(cli_cmd)
            proc = subprocess.run(cli_cmd, text=True, capture_output=True, timeout=TASK_TIMEOUT_SECONDS)
            exit_code = proc.returncode
            out = _trim(proc.stdout or "", MAX_STDOUT)
            err = f"{err}\n{_trim(proc.stderr or '', MAX_STDERR)}".strip()

        _mark_task_result(task, cmd_text, out, err, exit_code)
        db.commit()
        publish({"event": "task_finished", "plan_id": plan_id, "task_id": task_id, "status": task.status, "worker_id": WORKER_ID})

    except subprocess.TimeoutExpired as exc:
        task = db.get(Task, task_id)
        if task:
            _mark_task_result(task, task.command or "", "", f"task execution timed out after {TASK_TIMEOUT_SECONDS}s: {exc}", 124)
            db.commit()
            publish({"event": "task_finished", "plan_id": plan_id, "task_id": task_id, "status": task.status, "worker_id": WORKER_ID})
    except Exception as exc:
        logger.exception("task execution failed for plan=%s task=%s: %s", plan_id, task_id, exc)
        task = db.get(Task, task_id)
        if task and task.status == "RUNNING":
            _mark_task_result(task, task.command or "", "", f"unexpected worker error: {exc}", 1)
            db.commit()
            publish({"event": "task_finished", "plan_id": plan_id, "task_id": task_id, "status": task.status, "worker_id": WORKER_ID})
    finally:
        db.close()


def plan_progress(db, plan_id: int) -> Tuple[int, int]:
    total = db.query(Task).filter(Task.plan_id == plan_id).count()
    done = (
        db.query(Task)
        .filter(Task.plan_id == plan_id, Task.status.in_(["SUCCESS", "FAILED", "CANCELED", "SKIPPED"]))
        .count()
    )
    return total, done


def _run_and_clear(plan_id: int, task_id: int, inflight: Dict[int, Set[int]]) -> None:
    try:
        run_task(plan_id, task_id)
    finally:
        inflight.get(plan_id, set()).discard(task_id)


def _handle_signal(signum, _frame) -> None:
    logger.info("received signal %s, shutting down worker loop", signum)
    SHUTDOWN.set()


def main_loop() -> None:
    executor = ThreadPoolExecutor(max_workers=max(1, WORKER_MAX_THREADS))
    inflight: Dict[int, Set[int]] = {}

    try:
        while not SHUTDOWN.is_set():
            db = SessionLocal()
            try:
                plans = db.query(Plan).filter(Plan.status == "RUNNING").all()
                for p in plans:
                    inflight.setdefault(p.id, set())

                    cap = max(1, int(p.max_concurrency or 1))
                    current = len(inflight[p.id])
                    if current < cap:
                        pending = (
                            db.query(Task)
                            .filter(Task.plan_id == p.id, Task.status == "PENDING")
                            .order_by(Task.id.asc())
                            .limit(cap - current)
                            .all()
                        )
                        for t in pending:
                            inflight[p.id].add(t.id)
                            executor.submit(_run_and_clear, p.id, t.id, inflight)

                    total, done = plan_progress(db, p.id)
                    if total == 0 and not inflight[p.id]:
                        p.status = "COMPLETED"
                        p.updated_at = now()
                        db.commit()
                        publish({"event": "plan_completed", "plan_id": p.id, "status": p.status, "worker_id": WORKER_ID})
                    elif done == total and not inflight[p.id]:
                        failed = db.query(Task).filter(Task.plan_id == p.id, Task.status == "FAILED").count()
                        p.status = "FAILED" if failed else "COMPLETED"
                        p.updated_at = now()
                        db.commit()
                        publish({"event": "plan_completed", "plan_id": p.id, "status": p.status, "worker_id": WORKER_ID})

                publish({"event": "worker_heartbeat", "worker_id": WORKER_ID, "ts": str(now())})
            finally:
                db.close()

            SHUTDOWN.wait(POLL_SECONDS)
    finally:
        executor.shutdown(wait=True)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)
    main_loop()
