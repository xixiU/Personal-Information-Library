"""Source schemas - 信源相关的Pydantic模型."""
from typing import Optional
from datetime import datetime

from pydantic import BaseModel, Field


class SourceBase(BaseModel):
    """信源基础模型."""

    name: str = Field(..., min_length=1, max_length=200)
    url: str = Field(..., min_length=1, max_length=500)
    crawl_mode: str = Field(default="single_page")
    cron_expr: Optional[str] = None
    plugin_id: Optional[int] = None
    config: Optional[dict] = None
    category_id: Optional[int] = None
    status: str = Field(default="active")


class SourceCreate(SourceBase):
    """创建信源请求."""

    pass


class SourceUpdate(BaseModel):
    """更新信源请求."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    url: Optional[str] = Field(None, min_length=1, max_length=500)
    crawl_mode: Optional[str] = None
    cron_expr: Optional[str] = None
    plugin_id: Optional[int] = None
    config: Optional[dict] = None
    category_id: Optional[int] = None
    status: Optional[str] = None


class SourceResponse(SourceBase):
    """信源响应."""

    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
