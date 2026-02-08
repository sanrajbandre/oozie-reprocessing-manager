from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, ValidationInfo, field_validator, model_validator


RoleType = Literal["admin", "viewer"]
TaskType = Literal["workflow", "coordinator", "bundle"]

class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=128)
    password: str = Field(min_length=8, max_length=256)
    role: RoleType = "viewer"

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        trimmed = value.strip()
        if len(trimmed) < 3:
            raise ValueError("username must be at least 3 characters")
        return trimmed


class UserOut(BaseModel):
    id: int
    username: str
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TaskCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    type: TaskType
    job_id: str = Field(min_length=1, max_length=128)
    action: Optional[str] = Field(default="", max_length=128)
    date: Optional[str] = Field(default="", max_length=128)
    coordinator: Optional[str] = Field(default="", max_length=255)
    wf_failnodes: bool = False
    wf_skip_nodes: Optional[str] = Field(default="", max_length=1024)
    refresh: bool = False
    failed: bool = False
    extra_props: Optional[Dict[str, Any]] = Field(default_factory=dict)

    @field_validator("name", "job_id", "action", "date", "coordinator", "wf_skip_nodes")
    @classmethod
    def trim_text(cls, value: Optional[str], info: ValidationInfo) -> Optional[str]:
        if value is None:
            return None
        trimmed = value.strip()
        if info.field_name in {"name", "job_id"} and not trimmed:
            raise ValueError(f"{info.field_name} cannot be empty")
        return trimmed

    @model_validator(mode="after")
    def validate_by_type(self):
        if self.type == "coordinator":
            if not (self.action or self.date):
                raise ValueError("coordinator task requires 'action' or 'date'")
        if self.type == "bundle":
            if not (self.coordinator or self.date):
                raise ValueError("bundle task requires 'coordinator' or 'date'")
        return self


class PlanCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = Field(default="", max_length=4000)
    oozie_url: Optional[str] = Field(default="", max_length=512)
    use_rest: bool = False
    max_concurrency: int = Field(default=1, ge=1, le=64)
    tasks: List[TaskCreate] = Field(default_factory=list)

    @field_validator("name", "description", "oozie_url")
    @classmethod
    def trim_plan_text(cls, value: Optional[str], info: ValidationInfo) -> Optional[str]:
        if value is None:
            return None
        trimmed = value.strip()
        if info.field_name == "name" and not trimmed:
            raise ValueError("name cannot be empty")
        return trimmed


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
