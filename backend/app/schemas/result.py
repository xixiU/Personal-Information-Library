"""Result schemas - 结果相关的Pydantic模型."""
from typing import Optional
from datetime import datetime

from pydantic import BaseModel


class CrawlResultResponse(BaseModel):
    """爬取结果响应."""

    id: int
    task_id: int
    source_id: int
    url: str
    title: Optional[str] = None
    content: Optional[str] = None
    meta_data: Optional[dict] = None
    created_at: datetime

    class Config:
        from_attributes = True


class RefinedResultResponse(BaseModel):
    """精炼结果响应."""

    id: int
    crawl_result_id: int
    summary: Optional[str] = None
    keywords: Optional[list] = None
    category: Optional[str] = None
    quality_score: Optional[int] = None
    meta_data: Optional[dict] = None
    created_at: datetime

    class Config:
        from_attributes = True
