"""Database connection and session management."""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.config import settings

# Create engine
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables."""
    # 导入所有模型确保表被创建
    from app.models import source, task, result, plugin, task_log, category, notification  # noqa
    Base.metadata.create_all(bind=engine)
    _seed_default_plugins()


def _seed_default_plugins():
    """预置内置插件记录."""
    from app.models.plugin import Plugin

    db = SessionLocal()
    try:
        # 如果已有插件记录则跳过
        if db.query(Plugin).count() > 0:
            return

        default_plugins = [
            Plugin(
                name="generic",
                display_name="通用插件",
                description="适用于普通 HTML 页面的通用爬取插件",
                plugin_class="app.plugins.generic.GenericPlugin",
                domain_pattern=None,
                enabled=True,
            ),
            Plugin(
                name="rss",
                display_name="RSS 插件",
                description="适用于 RSS 2.0 / Atom 订阅源，自动解析所有条目",
                plugin_class="app.plugins.rss.RSSPlugin",
                domain_pattern=None,
                enabled=True,
            ),
        ]

        for p in default_plugins:
            db.add(p)

        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()
