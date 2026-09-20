"""Highlight model - 高亮笔记（任务 D）."""
from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index

from app.database import Base


class Highlight(Base):
    """高亮笔记模型."""

    __tablename__ = "highlights"

    id = Column(Integer, primary_key=True, index=True)
    refined_result_id = Column(
        Integer, ForeignKey("refined_results.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    highlight_text = Column(Text, nullable=False)  # 被高亮的原文（完整保存，不截断）
    note = Column(Text, nullable=True)  # 用户的批注（可选）
    position_start = Column(Integer, nullable=True)  # 在原文中的起始字符索引（可选）
    position_end = Column(Integer, nullable=True)  # 结束位置（可选）
    color = Column(String(20), nullable=False, default="yellow")  # yellow/green/blue/pink
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_highlights_result", "refined_result_id"),
        Index("idx_highlights_created", "created_at"),
    )
