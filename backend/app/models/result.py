"""Result models - 爬取结果和精炼结果."""
from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, JSON, Boolean, Index
from app.database import Base


class CrawlResult(Base):
    """Crawl result model."""

    __tablename__ = "crawl_results"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False, index=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False, index=True)
    url = Column(String(500), nullable=False, index=True)
    title = Column(String(500), nullable=True)
    content = Column(Text, nullable=True)  # Extracted main content
    raw_html = Column(Text, nullable=True)  # Original HTML
    meta_data = Column(JSON, nullable=True)  # Additional metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class RefinedResult(Base):
    """Refined result model."""

    __tablename__ = "refined_results"

    id = Column(Integer, primary_key=True, index=True)
    crawl_result_id = Column(Integer, ForeignKey("crawl_results.id"), nullable=False, unique=True, index=True)
    summary = Column(Text, nullable=True)
    keywords = Column(JSON, nullable=True)  # List of keywords
    category = Column(String(100), nullable=True)
    quality_score = Column(Integer, nullable=True)  # 质量评分 0-100
    interest_score = Column(Float, nullable=True, index=True)  # 兴趣匹配分 0.0~1.0
    meta_data = Column(JSON, nullable=True)  # Additional refined data
    is_read = Column(Boolean, nullable=False, default=False, index=True)  # 已读标记（任务 E）
    is_archived = Column(Boolean, nullable=False, default=False, index=True)  # 归档标记（任务 E）
    read_at = Column(DateTime, nullable=True)  # 标记已读的时间（任务 E）
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_results_read", "is_read", "created_at"),
        Index("idx_results_archived", "is_archived"),
    )
