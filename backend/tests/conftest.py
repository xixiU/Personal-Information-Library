"""Shared test fixtures."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import (
    Source,
    CrawlMode,
    SourceStatus,
    Task,
    TaskType,
    TaskStatus,
    CrawlResult,
    RefinedResult,
    Plugin,
    TaskLog,
    LogLevel,
)


@pytest.fixture
def engine():
    """Create in-memory SQLite engine for testing."""
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)
    eng.dispose()


@pytest.fixture
def db(engine):
    """Create a database session for testing."""
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def sample_source(db):
    """Create a sample source for testing."""
    source = Source(
        name="Test Source",
        url="https://example.com",
        crawl_mode=CrawlMode.SINGLE_PAGE,
        status=SourceStatus.ACTIVE,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


@pytest.fixture
def sample_task(db, sample_source):
    """Create a sample crawl task for testing."""
    task = Task(
        type=TaskType.CRAWL,
        status=TaskStatus.PENDING,
        priority=0,
        source_id=sample_source.id,
        url="https://example.com/page1",
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@pytest.fixture
def sample_crawl_result(db, sample_task, sample_source):
    """Create a sample crawl result for testing."""
    result = CrawlResult(
        task_id=sample_task.id,
        source_id=sample_source.id,
        url="https://example.com/page1",
        title="Test Page",
        content="This is test content.",
        raw_html="<html><body><p>This is test content.</p></body></html>",
        meta_data={"author": "tester"},
    )
    db.add(result)
    db.commit()
    db.refresh(result)
    return result


@pytest.fixture
def sample_plugin(db):
    """Create a sample plugin record for testing."""
    plugin = Plugin(
        name="generic",
        domain_pattern="*",
        plugin_class="app.plugins.generic.GenericPlugin",
        description="Generic crawler plugin",
        enabled=True,
    )
    db.add(plugin)
    db.commit()
    db.refresh(plugin)
    return plugin
