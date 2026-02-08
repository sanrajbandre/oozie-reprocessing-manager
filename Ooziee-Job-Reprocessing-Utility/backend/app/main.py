import logging
import re
from contextlib import asynccontextmanager

import redis
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from . import models
from .auth import decode_token, hash_password
from .broadcast import broadcaster, manager
from .db import Base, SessionLocal, engine
from .routes.auth import router as auth_router
from .routes.oozie_api import router as oozie_router
from .routes.plans import router as plans_router
from .routes.tasks import router as tasks_router
from .settings import settings

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)


def _parse_major(version: str) -> int:
    match = re.match(r"^\s*(\d+)", version)
    return int(match.group(1)) if match else 0


def _check_mysql_compatibility(db: Session) -> dict:
    row = db.execute(text("SELECT VERSION()")).scalar()
    version = str(row or "").strip()
    lower_version = version.lower()

    details = {
        "database_backend": "mysql",
        "database_version": version or "unknown",
    }

    if "mariadb" in lower_version:
        details["database_engine"] = "mariadb-compatible"
        details["mysql8_compatible"] = True
        return details

    details["database_engine"] = "mysql"
    major = _parse_major(version)
    details["mysql8_compatible"] = major >= 8
    if major < 8:
        raise RuntimeError(f"MySQL 8.0+ is required. Detected: {version}")
    return details


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate_runtime()
    if settings.auto_create_schema:
        logger.warning("AUTO_CREATE_SCHEMA=true is enabled. This should be used only for local/dev runs.")
        Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()
    try:
        if engine.url.get_backend_name() == "mysql":
            db_info = _check_mysql_compatibility(db)
            logger.info(
                "Database check passed: %s (%s)",
                db_info.get("database_engine"),
                db_info.get("database_version"),
            )

        if settings.bootstrap_admin_enabled and db.query(models.User).count() == 0:
            u = models.User(
                username=settings.bootstrap_admin_user,
                password_hash=hash_password(settings.bootstrap_admin_pass or ""),
                role="admin",
                is_active=True,
            )
            db.add(u)
            db.commit()
            logger.warning("Bootstrapped initial admin user '%s'", settings.bootstrap_admin_user)
    finally:
        db.close()

    await broadcaster.start()
    try:
        yield
    finally:
        await broadcaster.stop()


app = FastAPI(title="Oozie Reprocessing Manager", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(plans_router)
app.include_router(tasks_router)
app.include_router(oozie_router)


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/ready")
def ready():
    checks = {}

    db: Session = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "ok"
        checks["database_backend"] = engine.url.get_backend_name()
        if checks["database_backend"] == "mysql":
            checks.update(_check_mysql_compatibility(db))
    except Exception as exc:
        checks["database"] = f"error: {exc.__class__.__name__}"
    finally:
        db.close()

    try:
        redis.from_url(settings.redis_url, decode_responses=True).ping()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {exc.__class__.__name__}"

    if any(v != "ok" for v in checks.values()):
        raise HTTPException(status_code=503, detail={"status": "degraded", "checks": checks})

    return {"status": "ready", "checks": checks}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    token = websocket.query_params.get("token", "")
    if not token:
        await websocket.close(code=4401)
        return
    try:
        _ = decode_token(token)
    except Exception:
        await websocket.close(code=4401)
        return

    await manager.connect(websocket)
    try:
        while True:
            msg = await websocket.receive_text()
            if msg.strip().lower() == "ping":
                await websocket.send_text('{"event":"pong"}')
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception:
        await manager.disconnect(websocket)
