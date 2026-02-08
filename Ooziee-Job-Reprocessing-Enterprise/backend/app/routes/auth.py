from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
from .. import models, schemas
from ..auth import verify_password, create_access_token, hash_password, require_role, get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/login", response_model=schemas.TokenResponse)
def login(body: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == body.username).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(user.username, user.role)
    return schemas.TokenResponse(access_token=token, role=user.role)

@router.get("/me", response_model=schemas.UserOut)
def me(user=Depends(get_current_user)):
    return user

@router.post("/users", response_model=schemas.UserOut)
def create_user(body: schemas.UserCreate, db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    if body.role not in ("admin", "viewer"):
        raise HTTPException(status_code=400, detail="role must be admin or viewer")
    if db.query(models.User).filter(models.User.username == body.username).first():
        raise HTTPException(status_code=409, detail="username already exists")
    u = models.User(username=body.username, password_hash=hash_password(body.password), role=body.role, is_active=True)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u

@router.get("/users", response_model=list[schemas.UserOut])
def list_users(db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    return db.query(models.User).order_by(models.User.id.desc()).all()
