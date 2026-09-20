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
    interest_score: Optional[float] = None  # B2：兴趣智能排序
    meta_data: Optional[dict] = None
    is_read: bool = False  # 任务 E：已读标记
    is_archived: bool = False  # 任务 E：归档标记
    read_at: Optional[datetime] = None  # 任务 E：标记已读的时间
    highlight_count: int = 0  # 该结果的高亮数量（列表徽章用，避免 N+1）
    created_at: datetime

    class Config:
        from_attributes = True


class MarkReadRequest(BaseModel):
    """标记已读/未读请求（任务 E）."""

    is_read: bool = True


class ArchiveRequest(BaseModel):
    """归档/取消归档请求（任务 E）."""

    is_archived: bool = True
