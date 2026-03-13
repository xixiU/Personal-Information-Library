"""Plugin schemas - 插件相关的Pydantic模型."""
from typing import Optional
from datetime import datetime

from pydantic import BaseModel, Field


class PluginBase(BaseModel):
    """插件基础模型."""

    name: str = Field(..., min_length=1, max_length=100)
    display_name: Optional[str] = Field(None, max_length=200)
    domain_pattern: Optional[str] = Field(None, max_length=200)
    plugin_class: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    enabled: bool = Field(default=True)


class PluginCreate(PluginBase):
    """创建插件请求."""

    pass


class PluginUpdate(BaseModel):
    """更新插件请求."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    display_name: Optional[str] = Field(None, max_length=200)
    domain_pattern: Optional[str] = Field(None, max_length=200)
    plugin_class: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    enabled: Optional[bool] = None


class PluginResponse(PluginBase):
    """插件响应."""

    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
