"""Task schemas - 任务相关的Pydantic模型."""
from typing import Optional
from datetime import datetime

from pydantic import BaseModel


class TaskBase(BaseModel):
    """任务基础模型."""

    type: str
    source_id: int
    url: Optional[str] = None
    priority: int = 0
    payload: Optional[dict] = None


class TaskCreate(TaskBase):
    """创建任务请求."""

    pass


class TaskResponse(TaskBase):
    """任务响应."""

    id: int
    status: str
    parent_task_id: Optional[int] = None
    retry_count: int
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True
