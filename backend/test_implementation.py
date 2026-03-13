"""Quick test script to verify the implementation."""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import init_db, SessionLocal
from app.models.source import Source, CrawlMode
from app.models.task import Task, TaskType, TaskStatus
from app.core.scheduler import get_scheduler


async def test_basic_flow():
    """Test basic crawl flow."""
    print("Initializing database...")
    init_db()

    db = SessionLocal()

    try:
        # 创建测试信源
        print("Creating test source...")
        source = Source(
            name="Test Source",
            url="https://example.com",
            crawl_mode=CrawlMode.SINGLE_PAGE,
            status="active",
        )
        db.add(source)
        db.commit()
        db.refresh(source)
        print(f"Created source: {source.id}")

        # 创建测试任务
        print("Creating test task...")
        task = Task(
            type=TaskType.CRAWL,
            status=TaskStatus.PENDING,
            priority=10,
            source_id=source.id,
            url=source.url,
            payload={"depth": 0},
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        print(f"Created task: {task.id}")

        # 启动调度器
        print("Starting scheduler...")
        scheduler = get_scheduler()
        await scheduler.start()

        # 提交任务
        print("Submitting task...")
        await scheduler.submit_task(task.id, priority=task.priority)

        # 等待任务完成
        print("Waiting for task to complete...")
        for i in range(30):  # 最多等待30秒
            await asyncio.sleep(1)
            db.refresh(task)
            print(f"Task status: {task.status}")
            if task.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]:
                break

        # 停止调度器
        print("Stopping scheduler...")
        await scheduler.stop()

        # 检查结果
        if task.status == TaskStatus.SUCCESS:
            print("✓ Task completed successfully!")
            from app.models.result import CrawlResult

            result = (
                db.query(CrawlResult).filter(CrawlResult.task_id == task.id).first()
            )
            if result:
                print(f"✓ Crawl result created: {result.id}")
                print(f"  Title: {result.title}")
                print(f"  Content length: {len(result.content or '')}")
            else:
                print("✗ No crawl result found")
        else:
            print(f"✗ Task failed: {task.error_message}")

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(test_basic_flow())
