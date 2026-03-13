"""DB-U01/U02/U03: Data model CRUD tests."""
import pytest
from sqlalchemy import select

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


class TestSourceModel:
    """DB-U01: Source CRUD tests."""

    def test_create_source(self, db):
        """创建信源记录."""
        source = Source(
            name="Tech Blog",
            url="https://techblog.example.com",
            crawl_mode=CrawlMode.FULL_SITE,
            status=SourceStatus.ACTIVE,
            config={"max_depth": 3},
        )
        db.add(source)
        db.commit()
        db.refresh(source)

        assert source.id is not None
        assert source.name == "Tech Blog"
        assert source.crawl_mode == CrawlMode.FULL_SITE
        assert source.config == {"max_depth": 3}
        assert source.created_at is not None

    def test_create_source_with_cron(self, db):
        """创建带定时表达式的信源."""
        source = Source(
            name="Daily News",
            url="https://news.example.com",
            crawl_mode=CrawlMode.SINGLE_PAGE,
            cron_expr="0 8 * * *",
        )
        db.add(source)
        db.commit()

        assert source.cron_expr == "0 8 * * *"

    def test_source_unique_url(self, db, sample_source):
        """相同URL不能重复创建."""
        dup = Source(
            name="Duplicate",
            url=sample_source.url,
            crawl_mode=CrawlMode.SINGLE_PAGE,
        )
        db.add(dup)
        with pytest.raises(Exception):
            db.commit()

    def test_query_source_by_url(self, db, sample_source):
        """DB-U02: 按URL查询信源."""
        result = db.execute(
            select(Source).where(Source.url == "https://example.com")
        ).scalar_one()

        assert result.id == sample_source.id
        assert result.name == "Test Source"

    def test_query_source_by_status(self, db, sample_source):
        """DB-U02: 按状态查询信源."""
        paused = Source(
            name="Paused Source",
            url="https://paused.example.com",
            crawl_mode=CrawlMode.SINGLE_PAGE,
            status=SourceStatus.PAUSED,
        )
        db.add(paused)
        db.commit()

        active_sources = db.execute(
            select(Source).where(Source.status == SourceStatus.ACTIVE)
        ).scalars().all()

        assert len(active_sources) == 1
        assert active_sources[0].id == sample_source.id

    def test_update_source(self, db, sample_source):
        """DB-U03: 更新信源内容."""
        sample_source.name = "Updated Name"
        sample_source.crawl_mode = CrawlMode.FULL_SITE
        sample_source.config = {"max_depth": 5, "max_pages": 200}
        db.commit()
        db.refresh(sample_source)

        assert sample_source.name == "Updated Name"
        assert sample_source.crawl_mode == CrawlMode.FULL_SITE
        assert sample_source.config["max_pages"] == 200

    def test_update_source_status(self, db, sample_source):
        """DB-U03: 更新信源状态."""
        sample_source.status = SourceStatus.DISABLED
        db.commit()
        db.refresh(sample_source)

        assert sample_source.status == SourceStatus.DISABLED


class TestTaskModel:
    """Task CRUD tests."""

    def test_create_crawl_task(self, db, sample_source):
        """创建爬取任务."""
        task = Task(
            type=TaskType.CRAWL,
            status=TaskStatus.PENDING,
            priority=10,
            source_id=sample_source.id,
            url="https://example.com/article/1",
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        assert task.id is not None
        assert task.type == TaskType.CRAWL
        assert task.status == TaskStatus.PENDING
        assert task.priority == 10
        assert task.retry_count == 0

    def test_create_refine_task(self, db, sample_source):
        """创建精炼任务."""
        task = Task(
            type=TaskType.REFINE,
            status=TaskStatus.PENDING,
            priority=5,
            source_id=sample_source.id,
            payload={"crawl_result_id": 1, "mode": "summary"},
        )
        db.add(task)
        db.commit()

        assert task.type == TaskType.REFINE
        assert task.payload["mode"] == "summary"

    def test_create_child_task(self, db, sample_task, sample_source):
        """创建子任务（递归爬取）."""
        child = Task(
            type=TaskType.CRAWL,
            status=TaskStatus.PENDING,
            priority=0,
            source_id=sample_source.id,
            parent_task_id=sample_task.id,
            url="https://example.com/page2",
        )
        db.add(child)
        db.commit()

        assert child.parent_task_id == sample_task.id

    def test_query_tasks_by_status(self, db, sample_source):
        """按状态查询任务."""
        for i, status in enumerate([TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.PENDING]):
            task = Task(
                type=TaskType.CRAWL,
                status=status,
                priority=0,
                source_id=sample_source.id,
                url=f"https://example.com/p{i}",
            )
            db.add(task)
        db.commit()

        pending = db.execute(
            select(Task).where(Task.status == TaskStatus.PENDING)
        ).scalars().all()

        assert len(pending) == 2

    def test_update_task_status(self, db, sample_task):
        """更新任务状态."""
        sample_task.status = TaskStatus.RUNNING
        db.commit()
        db.refresh(sample_task)
        assert sample_task.status == TaskStatus.RUNNING

        sample_task.status = TaskStatus.SUCCESS
        db.commit()
        db.refresh(sample_task)
        assert sample_task.status == TaskStatus.SUCCESS

    def test_update_task_retry(self, db, sample_task):
        """更新任务重试计数."""
        sample_task.status = TaskStatus.FAILED
        sample_task.retry_count = 1
        sample_task.error_message = "Connection timeout"
        db.commit()
        db.refresh(sample_task)

        assert sample_task.retry_count == 1
        assert sample_task.error_message == "Connection timeout"


class TestCrawlResultModel:
    """CrawlResult CRUD tests."""

    def test_create_crawl_result(self, db, sample_task, sample_source):
        """创建爬取结果."""
        result = CrawlResult(
            task_id=sample_task.id,
            source_id=sample_source.id,
            url="https://example.com/page1",
            title="Test Article",
            content="Article body text here.",
            meta_data={"author": "John", "keywords": "test,article"},
        )
        db.add(result)
        db.commit()
        db.refresh(result)

        assert result.id is not None
        assert result.title == "Test Article"
        assert result.meta_data["author"] == "John"

    def test_query_result_by_source(self, db, sample_crawl_result, sample_source):
        """按信源查询爬取结果."""
        results = db.execute(
            select(CrawlResult).where(CrawlResult.source_id == sample_source.id)
        ).scalars().all()

        assert len(results) == 1
        assert results[0].url == "https://example.com/page1"

    def test_query_result_by_url(self, db, sample_crawl_result):
        """按URL查询爬取结果."""
        result = db.execute(
            select(CrawlResult).where(CrawlResult.url == "https://example.com/page1")
        ).scalar_one()

        assert result.title == "Test Page"

    def test_update_crawl_result(self, db, sample_crawl_result):
        """更新爬取结果."""
        sample_crawl_result.title = "Updated Title"
        sample_crawl_result.content = "Updated content."
        db.commit()
        db.refresh(sample_crawl_result)

        assert sample_crawl_result.title == "Updated Title"


class TestRefinedResultModel:
    """RefinedResult CRUD tests."""

    def test_create_refined_result(self, db, sample_crawl_result):
        """创建精炼结果."""
        refined = RefinedResult(
            crawl_result_id=sample_crawl_result.id,
            summary="This is a test summary.",
            keywords=["test", "example"],
            category="technology",
            meta_data={"model": "gpt-4o-mini", "tokens": 150},
        )
        db.add(refined)
        db.commit()
        db.refresh(refined)

        assert refined.id is not None
        assert refined.summary == "This is a test summary."
        assert refined.keywords == ["test", "example"]
        assert refined.category == "technology"

    def test_query_refined_by_crawl_result(self, db, sample_crawl_result):
        """按爬取结果查询精炼结果."""
        refined = RefinedResult(
            crawl_result_id=sample_crawl_result.id,
            summary="Summary text",
            keywords=["k1"],
        )
        db.add(refined)
        db.commit()

        result = db.execute(
            select(RefinedResult).where(
                RefinedResult.crawl_result_id == sample_crawl_result.id
            )
        ).scalar_one()

        assert result.summary == "Summary text"


class TestPluginModel:
    """Plugin CRUD tests."""

    def test_create_plugin(self, db):
        """创建插件记录."""
        plugin = Plugin(
            name="rss",
            domain_pattern=None,
            plugin_class="app.plugins.rss.RSSPlugin",
            description="RSS feed parser",
            enabled=True,
        )
        db.add(plugin)
        db.commit()
        db.refresh(plugin)

        assert plugin.id is not None
        assert plugin.name == "rss"

    def test_plugin_unique_name(self, db, sample_plugin):
        """插件名称唯一约束."""
        dup = Plugin(
            name=sample_plugin.name,
            plugin_class="some.other.Class",
        )
        db.add(dup)
        with pytest.raises(Exception):
            db.commit()

    def test_query_enabled_plugins(self, db, sample_plugin):
        """查询启用的插件."""
        disabled = Plugin(
            name="disabled_plugin",
            plugin_class="some.Class",
            enabled=False,
        )
        db.add(disabled)
        db.commit()

        enabled = db.execute(
            select(Plugin).where(Plugin.enabled == True)
        ).scalars().all()

        assert len(enabled) == 1
        assert enabled[0].name == "generic"

    def test_update_plugin(self, db, sample_plugin):
        """更新插件信息."""
        sample_plugin.description = "Updated description"
        sample_plugin.enabled = False
        db.commit()
        db.refresh(sample_plugin)

        assert sample_plugin.description == "Updated description"
        assert sample_plugin.enabled is False


class TestTaskLogModel:
    """TaskLog CRUD tests."""

    def test_create_task_log(self, db, sample_task):
        """创建任务日志."""
        log = TaskLog(
            task_id=sample_task.id,
            level=LogLevel.INFO,
            message="Task started",
        )
        db.add(log)
        db.commit()
        db.refresh(log)

        assert log.id is not None
        assert log.level == LogLevel.INFO

    def test_query_logs_by_task(self, db, sample_task):
        """按任务查询日志."""
        for level, msg in [
            (LogLevel.INFO, "Started"),
            (LogLevel.WARNING, "Slow response"),
            (LogLevel.ERROR, "Failed"),
        ]:
            db.add(TaskLog(task_id=sample_task.id, level=level, message=msg))
        db.commit()

        logs = db.execute(
            select(TaskLog).where(TaskLog.task_id == sample_task.id)
        ).scalars().all()

        assert len(logs) == 3

        errors = db.execute(
            select(TaskLog).where(
                TaskLog.task_id == sample_task.id,
                TaskLog.level == LogLevel.ERROR,
            )
        ).scalars().all()

        assert len(errors) == 1
        assert errors[0].message == "Failed"
