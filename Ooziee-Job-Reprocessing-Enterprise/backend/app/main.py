from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from .settings import settings
from .db import engine, SessionLocal, Base
from . import models
from .auth import hash_password, decode_token
from .broadcast import manager, broadcaster

from .routes.auth import router as auth_router
from .routes.plans import router as plans_router
from .routes.tasks import router as tasks_router
from .routes.oozie_api import router as oozie_router

app = FastAPI(title="Oozie Reprocessing Manager", version="0.1.0")

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

@app.on_event("startup")
async def on_startup():
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    try:
        if db.query(models.User).count() == 0:
            u = models.User(
                username=settings.bootstrap_admin_user,
                password_hash=hash_password(settings.bootstrap_admin_pass),
                role="admin",
                is_active=True,
            )
            db.add(u)
            db.commit()
    finally:
        db.close()
    await broadcaster.start()

@app.on_event("shutdown")
async def on_shutdown():
    await broadcaster.stop()

@app.get("/health")
def health():
    return {"ok": True}

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
            _ = await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception:
        await manager.disconnect(websocket)
