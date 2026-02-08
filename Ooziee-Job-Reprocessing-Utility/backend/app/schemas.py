from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str

class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "viewer"

class UserOut(BaseModel):
    id: int
    username: str
    role: str
    is_active: bool
    created_at: datetime
    class Config:
        from_attributes = True

class TaskCreate(BaseModel):
    name: str
    type: str
    job_id: str
    action: Optional[str] = ""
    date: Optional[str] = ""
    coordinator: Optional[str] = ""
    wf_failnodes: Optional[bool] = False
    wf_skip_nodes: Optional[str] = ""
    refresh: Optional[bool] = False
    failed: Optional[bool] = False
    extra_props: Optional[Dict[str, Any]] = Field(default_factory=dict)

class PlanCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    oozie_url: Optional[str] = ""
    use_rest: Optional[bool] = False
    max_concurrency: Optional[int] = 1
    tasks: List[TaskCreate] = Field(default_factory=list)

class PlanOut(BaseModel):
    id: int
    name: str
    description: str
    status: str
    oozie_url: str
    use_rest: bool
    max_concurrency: int
    created_by: str
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True

class TaskOut(BaseModel):
    id: int
    plan_id: int
    name: str
    type: str
    job_id: str
    action: str
    date: str
    coordinator: str
    wf_failnodes: bool
    wf_skip_nodes: str
    refresh: bool
    failed: bool
    extra_props: Dict[str, Any]
    status: str
    attempt: int
    command: str
    stdout: str
    stderr: str
    exit_code: Optional[int]
    pid: Optional[int]
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    class Config:
        from_attributes = True

class PlanDetail(BaseModel):
    plan: PlanOut
    tasks: List[TaskOut]

class PlanActionResponse(BaseModel):
    plan_id: int
    status: str
