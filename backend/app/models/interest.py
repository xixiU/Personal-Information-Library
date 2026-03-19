"""Interest models - 用户反馈和兴趣点."""
from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, Index, JSON
from app.database import Base


class UserFeedback(Base):
    """用户反馈模型."""

    __tablename__ = "user_feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    refined_result_id = Column(Integer, ForeignKey("refined_results.id"), nullable=False, index=True)
    action = Column(String(20), nullable=False)  # like | collect | dislike | comment
    comment_text = Column(Text, nullable=True)  # action=comment 时有值
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    __table_args__ = (
        Index("ix_user_feedbacks_result_action", "refined_result_id", "action"),
    )


class InterestPoint(Base):
    """兴趣点模型."""

    __tablename__ = "interest_points"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    source = Column(String(20), nullable=False, default="manual")  # manual | ai_discovered
    weight = Column(Float, nullable=False, default=0.5)  # 0.0~1.0
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True, index=True)
    keywords = Column(JSON, nullable=False, default=list)  # ["rust", "wasm"]
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
