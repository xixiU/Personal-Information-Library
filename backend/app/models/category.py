"""Category model - 分类配置."""
from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime
from app.database import Base


class Category(Base):
    """Category model."""

    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(String(500), nullable=True)
    color = Column(String(20), nullable=False, default="#1677ff")
    refine_prompt_system = Column(Text, nullable=False)  # 总结重点
    quality_criteria = Column(Text, nullable=False)  # 质量评分标准
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
