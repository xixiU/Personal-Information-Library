"""Task log model - 任务执行日志."""
from datetime import datetime
from enum import Enum

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from app.database import Base


class LogLevel(str, Enum):
    """Log level enum."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class TaskLog(Base):
    """Task log model."""

    __tablename__ = "task_logs"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False, index=True)
    level = Column(String(20), nullable=False, default=LogLevel.INFO)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
