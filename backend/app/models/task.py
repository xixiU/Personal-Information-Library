"""Task model - 任务记录."""
from datetime import datetime
from enum import Enum

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from app.database import Base


class TaskType(str, Enum):
    """Task type enum."""

    CRAWL = "crawl"
    REFINE = "refine"


class TaskStatus(str, Enum):
    """Task status enum."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


class Task(Base):
    """Task model."""

    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(20), nullable=False, index=True)
    status = Column(String(20), nullable=False, default=TaskStatus.PENDING, index=True)
    priority = Column(Integer, nullable=False, default=0)  # Higher = more priority
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False, index=True)
    parent_task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)  # For recursive tasks
    url = Column(String(500), nullable=True)  # URL to crawl (for crawl tasks)
    payload = Column(JSON, nullable=True)  # Additional task data
    retry_count = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
