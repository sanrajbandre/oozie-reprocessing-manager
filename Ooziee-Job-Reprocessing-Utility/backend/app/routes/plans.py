from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from ..db import get_db
from .. import models, schemas
from ..auth import get_current_user, require_role
from ..events import publish_event

router = APIRouter(prefix="/api/plans", tags=["plans"])

@router.post("", response_model=schemas.PlanOut)
def create_plan(body: schemas.PlanCreate, db: Session = Depends(get_db), user=Depends(require_role("admin"))):
    p = models.Plan(
        name=body.name,
        description=body.description or "",
        status="DRAFT",
        oozie_url=body.oozie_url or "",
        use_rest=bool(body.use_rest),
        max_concurrency=int(body.max_concurrency or 1),
        created_by=user.username,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(p)
    db.flush()
    for t in body.tasks:
        task = models.Task(
            plan_id=p.id,
            name=t.name,
            type=t.type,
            job_id=t.job_id,
            action=t.action or "",
            date=t.date or "",
            coordinator=t.coordinator or "",
            wf_failnodes=bool(t.wf_failnodes),
            wf_skip_nodes=t.wf_skip_nodes or "",
            refresh=bool(t.refresh),
            failed=bool(t.failed),
            extra_props=t.extra_props or {},
            status="PENDING",
            attempt=0,
        )
        db.add(task)
    db.commit()
    db.refresh(p)
    publish_event({"event":"plan_created","plan_id":p.id})
    return p

@router.get("", response_model=list[schemas.PlanOut])
def list_plans(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return db.query(models.Plan).order_by(models.Plan.id.desc()).all()

@router.get("/{plan_id}", response_model=schemas.PlanDetail)
def get_plan(plan_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    p = db.query(models.Plan).filter(models.Plan.id == plan_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="plan not found")
    tasks = db.query(models.Task).filter(models.Task.plan_id == plan_id).order_by(models.Task.id.asc()).all()
    return schemas.PlanDetail(plan=p, tasks=tasks)

def _set_plan_status(db: Session, plan_id: int, status: str):
    p = db.query(models.Plan).filter(models.Plan.id == plan_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="plan not found")
    p.status = status
    p.updated_at = datetime.utcnow()
    db.commit()
    publish_event({"event":"plan_status","plan_id":plan_id,"status":status})
    return p

@router.post("/{plan_id}/start", response_model=schemas.PlanActionResponse)
def start_plan(plan_id: int, db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    p = _set_plan_status(db, plan_id, "RUNNING")
    return schemas.PlanActionResponse(plan_id=p.id, status=p.status)

@router.post("/{plan_id}/pause", response_model=schemas.PlanActionResponse)
def pause_plan(plan_id: int, db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    p = _set_plan_status(db, plan_id, "PAUSED")
    return schemas.PlanActionResponse(plan_id=p.id, status=p.status)

@router.post("/{plan_id}/resume", response_model=schemas.PlanActionResponse)
def resume_plan(plan_id: int, db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    p = _set_plan_status(db, plan_id, "RUNNING")
    return schemas.PlanActionResponse(plan_id=p.id, status=p.status)

@router.post("/{plan_id}/stop", response_model=schemas.PlanActionResponse)
def stop_plan(plan_id: int, db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    p = _set_plan_status(db, plan_id, "STOPPED")
    db.query(models.Task).filter(models.Task.plan_id==plan_id, models.Task.status=="PENDING").update({"status":"CANCELED"})
    db.commit()
    publish_event({"event":"plan_stopped","plan_id":plan_id})
    return schemas.PlanActionResponse(plan_id=p.id, status=p.status)
