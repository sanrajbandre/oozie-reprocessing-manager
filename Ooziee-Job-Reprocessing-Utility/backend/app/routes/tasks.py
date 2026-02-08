from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from ..db import get_db
from .. import models
from ..auth import require_role
from ..events import publish_event

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

@router.post("/{task_id}/cancel")
def cancel_task(task_id: int, db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    t = db.query(models.Task).filter(models.Task.id==task_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="task not found")
    if t.status in ("SUCCESS","FAILED","CANCELED","SKIPPED"):
        return {"status": t.status}
    t.status = "CANCELED"
    t.ended_at = datetime.utcnow()
    db.commit()
    publish_event({"event":"task_canceled","plan_id":t.plan_id,"task_id":t.id})
    return {"status": t.status}

@router.post("/{task_id}/retry")
def retry_task(task_id: int, db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    t = db.query(models.Task).filter(models.Task.id==task_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="task not found")
    t.status = "PENDING"
    t.attempt = int(t.attempt or 0) + 1
    t.stdout = ""
    t.stderr = ""
    t.exit_code = None
    t.started_at = None
    t.ended_at = None
    t.pid = None
    db.commit()
    publish_event({"event":"task_retried","plan_id":t.plan_id,"task_id":t.id})
    return {"status": t.status}
