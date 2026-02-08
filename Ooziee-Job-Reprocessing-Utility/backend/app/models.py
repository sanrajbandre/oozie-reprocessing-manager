from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .db import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(128), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(32), nullable=False, default="admin")  # admin/viewer
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Plan(Base):
    __tablename__ = "plans"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    status = Column(String(32), nullable=False, default="DRAFT")
    oozie_url = Column(String(512), default="")
    use_rest = Column(Boolean, default=False)
    max_concurrency = Column(Integer, default=1)
    created_by = Column(String(128), default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tasks = relationship("Task", back_populates="plan", cascade="all, delete-orphan")


class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False)
    name = Column(String(255), nullable=False)
    type = Column(String(32), nullable=False)  # workflow/coordinator/bundle
    job_id = Column(String(128), nullable=False)

    action = Column(String(128), default="")
    date = Column(String(128), default="")
    coordinator = Column(String(255), default="")

    wf_failnodes = Column(Boolean, default=False)
    wf_skip_nodes = Column(String(1024), default="")

    refresh = Column(Boolean, default=False)
    failed = Column(Boolean, default=False)

    extra_props = Column(JSON, default=lambda: {})

    status = Column(String(32), nullable=False, default="PENDING")
    attempt = Column(Integer, default=0)

    command = Column(Text, default="")
    stdout = Column(Text, default="")
    stderr = Column(Text, default="")
    exit_code = Column(Integer, default=None)
    pid = Column(Integer, default=None)

    started_at = Column(DateTime, default=None)
    ended_at = Column(DateTime, default=None)

    plan = relationship("Plan", back_populates="tasks")
