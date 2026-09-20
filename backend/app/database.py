"""Database connection and session management."""
import logging

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.config import settings

logger = logging.getLogger(__name__)

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
    from app.models import (  # noqa
        source, task, result, plugin, task_log, category, notification, interest, highlight,
    )

    # 轻量迁移：添加 source_type 字段（如果不存在）
    _migrate_add_source_type()

    # 轻量迁移：为 refined_results 添加已读/归档字段（任务 E）
    _migrate_add_read_archive_columns()

    Base.metadata.create_all(bind=engine)
    _seed_default_plugins()


def _migrate_add_source_type():
    """轻量迁移：为 sources 表添加 source_type 字段."""
    import sqlite3

    # 只处理 SQLite
    if "sqlite" not in settings.database_url:
        return

    db_path = settings.database_url.replace("sqlite:///", "")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 检查字段是否已存在
        cursor.execute("PRAGMA table_info(sources)")
        columns = [row[1] for row in cursor.fetchall()]

        if "source_type" not in columns:
            logger.info("Adding source_type column to sources table")
            cursor.execute("ALTER TABLE sources ADD COLUMN source_type VARCHAR(20)")
            conn.commit()
            logger.info("source_type column added successfully")

        conn.close()
    except Exception as e:
        logger.warning(f"Failed to add source_type column (may not exist yet): {e}")


def _migrate_add_read_archive_columns():
    """轻量迁移：为 refined_results 表添加 is_read/is_archived/read_at 字段（任务 E）."""
    import sqlite3

    # 只处理 SQLite
    if "sqlite" not in settings.database_url:
        return

    db_path = settings.database_url.replace("sqlite:///", "")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 表可能尚未创建（首次启动），此时 create_all 会带上新字段，跳过即可
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='refined_results'"
        )
        if not cursor.fetchone():
            conn.close()
            return

        cursor.execute("PRAGMA table_info(refined_results)")
        columns = [row[1] for row in cursor.fetchall()]

        if "is_read" not in columns:
            logger.info("Adding is_read column to refined_results table")
            cursor.execute(
                "ALTER TABLE refined_results ADD COLUMN is_read BOOLEAN DEFAULT 0"
            )
        if "is_archived" not in columns:
            logger.info("Adding is_archived column to refined_results table")
            cursor.execute(
                "ALTER TABLE refined_results ADD COLUMN is_archived BOOLEAN DEFAULT 0"
            )
        if "read_at" not in columns:
            logger.info("Adding read_at column to refined_results table")
            cursor.execute(
                "ALTER TABLE refined_results ADD COLUMN read_at DATETIME"
            )

        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning(f"Failed to add read/archive columns (may not exist yet): {e}")


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
