"""Highlight schemas - 高亮笔记相关 Pydantic 模型（任务 D）."""
from typing import Optional
from datetime import datetime

from pydantic import BaseModel, Field


class HighlightCreate(BaseModel):
    """创建高亮请求."""

    refined_result_id: int
    highlight_text: str = Field(..., min_length=1)
    note: Optional[str] = None
    position_start: Optional[int] = None
    position_end: Optional[int] = None
    color: str = Field(default="yellow", pattern="^(yellow|green|blue|pink)$")


class HighlightUpdate(BaseModel):
    """更新高亮请求（主要改批注）."""

    note: Optional[str] = None
    color: Optional[str] = Field(None, pattern="^(yellow|green|blue|pink)$")


class HighlightResponse(BaseModel):
    """高亮响应."""

    id: int
    refined_result_id: int
    highlight_text: str
    note: Optional[str] = None
    position_start: Optional[int] = None
    position_end: Optional[int] = None
    color: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
