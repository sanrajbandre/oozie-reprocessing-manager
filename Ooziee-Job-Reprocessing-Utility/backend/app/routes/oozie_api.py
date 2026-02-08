from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
from .. import models
from ..auth import get_current_user
from ..settings import settings
from ..oozie import OozieClient

router = APIRouter(prefix="/api/oozie", tags=["oozie"])

@router.get("/job/{job_id}")
def job_info(job_id: str, plan_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    p = db.query(models.Plan).filter(models.Plan.id == plan_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="plan not found")
    oozie_url = (p.oozie_url or settings.oozie_default_url).strip()
    if not oozie_url:
        raise HTTPException(status_code=400, detail="oozie_url not configured for plan")
    client = OozieClient(oozie_url)
    return client.job_info(job_id)
