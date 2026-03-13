"""Plugin model - 插件注册表."""
from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from app.database import Base


class Plugin(Base):
    """Plugin model."""

    __tablename__ = "plugins"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    display_name = Column(String(200), nullable=True)  # 显示名称
    domain_pattern = Column(String(200), nullable=True)  # Domain pattern for matching
    plugin_class = Column(String(200), nullable=False)  # Python class path
    description = Column(Text, nullable=True)
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
