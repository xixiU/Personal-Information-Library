"""Source model - 信源配置."""
from datetime import datetime
from enum import Enum

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON
from app.database import Base


class CrawlMode(str, Enum):
    """Crawl mode enum."""

    SINGLE_PAGE = "single_page"
    FULL_SITE = "full_site"


class SourceStatus(str, Enum):
    """Source status enum."""

    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"


class Source(Base):
    """Source model."""

    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    url = Column(String(500), nullable=False, unique=True, index=True)
    crawl_mode = Column(String(20), nullable=False, default=CrawlMode.SINGLE_PAGE)
    cron_expr = Column(String(100), nullable=True)  # Cron expression for scheduling
    plugin_id = Column(Integer, nullable=True)  # Foreign key to plugins table
    config = Column(JSON, nullable=True)  # Additional configuration
    status = Column(String(20), nullable=False, default=SourceStatus.ACTIVE)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
