import os
import time
import json
import subprocess
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from typing import Dict

import redis
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
from app.models import Plan, Task  # type: ignore
from app.settings import Settings  # type: ignore
from app.oozie import OozieClient  # type: ignore

settings = Settings()

ENGINE = create_engine(settings.db_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=ENGINE, autocommit=False, autoflush=False)

REDIS = redis.from_url(settings.redis_url, decode_responses=True)

OOZIE_BIN = os.environ.get("OOZIE_BIN", "oozie")
PRE_TASK_SHELL_CMD = os.environ.get("PRE_TASK_SHELL_CMD", "").strip()

POLL_SECONDS = int(os.environ.get("WORKER_POLL_SECONDS", "3"))
MAX_STDOUT = int(os.environ.get("MAX_STDOUT", "50000"))
MAX_STDERR = int(os.environ.get("MAX_STDERR", "50000"))

def publish(event: dict):
    try:
        REDIS.publish(settings.redis_channel, json.dumps(event, default=str))
    except Exception:
        pass

def now():
    return datetime.utcnow()

def build_cli_command(plan: Plan, task: Task) -> str:
    oozie_url = (plan.oozie_url or settings.oozie_default_url).strip()
    if not oozie_url:
        raise RuntimeError("oozie_url not configured")

    cmd = [OOZIE_BIN, "job", "-oozie", oozie_url, "-rerun", task.job_id]

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
            cmd.extend(["-D" + k + "=" + v])
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

    return " ".join(cmd)

def run_task(plan_id: int, task_id: int):
    db = SessionLocal()
    try:
        plan = db.get(Plan, plan_id)
        task = db.get(Task, task_id)
        if not plan or not task:
            return
        if plan.status != "RUNNING":
            return
        if task.status != "PENDING":
            return

        task.status = "RUNNING"
        task.started_at = now()
        task.attempt = int(task.attempt or 0) + 1
        db.commit()
        publish({"event":"task_started","plan_id":plan_id,"task_id":task_id})

        if PRE_TASK_SHELL_CMD:
            pre = subprocess.run(PRE_TASK_SHELL_CMD, shell=True, text=True, capture_output=True)
            if pre.returncode != 0:
                task.status = "FAILED"
                task.stderr = (pre.stderr or "")[:MAX_STDERR]
                task.stdout = (pre.stdout or "")[:MAX_STDOUT]
                task.exit_code = pre.returncode
                task.ended_at = now()
                db.commit()
                publish({"event":"task_finished","plan_id":plan_id,"task_id":task_id,"status":task.status})
                return

        exit_code = 0
        out = ""
        err = ""
        cmd = ""

        if plan.use_rest:
            try:
                client = OozieClient((plan.oozie_url or settings.oozie_default_url).strip())
                conf = {}
                params = {}
                if task.type == "workflow":
                    if task.wf_skip_nodes:
                        conf["oozie.wf.rerun.skip.nodes"] = task.wf_skip_nodes
                    else:
                        conf["oozie.wf.rerun.failnodes"] = "true" if task.wf_failnodes else "false"
                    for k, v in (task.extra_props or {}).items():
                        conf[str(k)] = str(v)
                elif task.type == "coordinator":
                    if task.action:
                        params["action"] = task.action
                    if task.date:
                        params["date"] = task.date
                    if task.failed:
                        params["failed"] = "true"
                    if task.refresh:
                        params["refresh"] = "true"
                elif task.type == "bundle":
                    if task.coordinator:
                        params["coordinator"] = task.coordinator
                    if task.date:
                        params["date"] = task.date
                    if task.refresh:
                        params["refresh"] = "true"
                resp = client.rerun(task.job_id, conf=conf if conf else None, params=params if params else None)
                cmd = f"REST PUT {client.base_url}/v2/job/{task.job_id}?action=rerun"
                out = json.dumps(resp, default=str)
                err = ""
                exit_code = 0
            except Exception:
                plan.use_rest = False
                db.commit()

        if not plan.use_rest:
            cmd = build_cli_command(plan, task)
            proc = subprocess.run(cmd, shell=True, text=True, capture_output=True)
            exit_code = proc.returncode
            out = (proc.stdout or "")[:MAX_STDOUT]
            err = (proc.stderr or "")[:MAX_STDERR]

        task.command = cmd
        task.stdout = out
        task.stderr = err
        task.exit_code = exit_code
        task.ended_at = now()
        task.status = "SUCCESS" if exit_code == 0 else "FAILED"
        db.commit()
        publish({"event":"task_finished","plan_id":plan_id,"task_id":task_id,"status":task.status})
    finally:
        db.close()

def plan_progress(db, plan_id: int):
    total = db.query(Task).filter(Task.plan_id==plan_id).count()
    done = db.query(Task).filter(Task.plan_id==plan_id, Task.status.in_(["SUCCESS","FAILED","CANCELED","SKIPPED"])).count()
    return total, done

def _run_and_clear(plan_id: int, task_id: int, inflight: Dict[int, set]):
    try:
        run_task(plan_id, task_id)
    finally:
        inflight.get(plan_id, set()).discard(task_id)

def main_loop():
    executor = ThreadPoolExecutor(max_workers=int(os.environ.get("WORKER_MAX_THREADS", "32")))
    inflight: Dict[int, set] = {}

    while True:
        db = SessionLocal()
        try:
            plans = db.query(Plan).filter(Plan.status.in_(["RUNNING","PAUSED","STOPPED"])).all()
            for p in plans:
                inflight.setdefault(p.id, set())
                if p.status != "RUNNING":
                    continue

                cap = max(1, int(p.max_concurrency or 1))
                current = len(inflight[p.id])
                if current >= cap:
                    continue

                pending = db.query(Task).filter(Task.plan_id==p.id, Task.status=="PENDING").order_by(Task.id.asc()).limit(cap-current).all()
                for t in pending:
                    inflight[p.id].add(t.id)
                    executor.submit(_run_and_clear, p.id, t.id, inflight)

                total, done = plan_progress(db, p.id)
                if total > 0 and done == total:
                    failed = db.query(Task).filter(Task.plan_id==p.id, Task.status=="FAILED").count()
                    p.status = "FAILED" if failed else "COMPLETED"
                    p.updated_at = now()
                    db.commit()
                    publish({"event":"plan_completed","plan_id":p.id,"status":p.status})

            publish({"event":"worker_heartbeat","ts":str(now())})
        finally:
            db.close()

        time.sleep(POLL_SECONDS)

if __name__ == "__main__":
    main_loop()
