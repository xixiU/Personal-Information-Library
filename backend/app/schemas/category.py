"""Category schemas - 分类相关的Pydantic模型."""
from typing import Optional
from datetime import datetime

from pydantic import BaseModel, Field


class CategoryCreate(BaseModel):
    """创建分类请求."""

    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    color: str = Field(default="#1677ff", max_length=20)
    refine_prompt_system: str
    quality_criteria: str


class CategoryUpdate(BaseModel):
    """更新分类请求."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    color: Optional[str] = Field(None, max_length=20)
    refine_prompt_system: Optional[str] = None
    quality_criteria: Optional[str] = None


class CategoryResponse(BaseModel):
    """分类响应."""

    id: int
    name: str
    description: Optional[str] = None
    color: str = "#1677ff"
    refine_prompt_system: str
    quality_criteria: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
