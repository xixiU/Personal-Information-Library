"""Task scheduler - 任务调度器."""
import asyncio
import logging
from typing import Optional
from datetime import datetime

from sqlalchemy.orm import Session
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import settings
from app.database import SessionLocal
from app.models.task import Task, TaskStatus, TaskType
from app.models.source import Source, SourceStatus
from app.core.crawler import CrawlerEngine
from app.core.refiner import RefinerEngine

logger = logging.getLogger(__name__)


class TaskScheduler:
    """任务调度器，负责任务队列管理和执行."""

    def __init__(self):
        """初始化调度器."""
        self.queue: asyncio.PriorityQueue = asyncio.PriorityQueue(
            maxsize=settings.task_queue_size
        )
        self.running = False
        self.workers: list[asyncio.Task] = []
        self.crawler_engine = CrawlerEngine()
        self.refiner_engine = RefinerEngine()

        # APScheduler for cron-based scheduling
        self.apscheduler = AsyncIOScheduler()
        self.scheduled_jobs = {}  # source_id -> job_id mapping

    async def start(self):
        """启动调度器和worker."""
        if self.running:
            logger.warning("Scheduler already running")
            return

        self.running = True
        logger.info(f"Starting scheduler with {settings.crawler_max_workers} workers")

        # 启动APScheduler
        self.apscheduler.start()
        logger.info("APScheduler started")

        # 加载所有信源的定时任务
        await self._load_scheduled_sources()

        # 启动worker
        for i in range(settings.crawler_max_workers):
            worker = asyncio.create_task(self._worker(i))
            self.workers.append(worker)

        # 恢复未完成的任务
        await self._recover_pending_tasks()

    async def stop(self):
        """停止调度器."""
        logger.info("Stopping scheduler")
        self.running = False

        # 停止APScheduler
        self.apscheduler.shutdown()
        logger.info("APScheduler stopped")

        # 等待所有worker完成
        for worker in self.workers:
            worker.cancel()
        await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()

    async def submit_task(self, task_id: int, priority: int = 0) -> bool:
        """
        提交任务到队列.

        Args:
            task_id: 任务ID
            priority: 优先级（数字越小越优先）

        Returns:
            是否成功提交
        """
        try:
            # 优先级队列使用负数，使得数字越大优先级越高
            await self.queue.put((-priority, task_id))
            logger.info(f"Task {task_id} submitted with priority {priority}")
            return True
        except asyncio.QueueFull:
            logger.error(f"Queue full, cannot submit task {task_id}")
            return False

    async def _worker(self, worker_id: int):
        """Worker循环，从队列取任务并执行."""
        logger.info(f"Worker {worker_id} started")

        while self.running:
            try:
                # 从队列获取任务（带超时，避免阻塞shutdown）
                try:
                    priority, task_id = await asyncio.wait_for(
                        self.queue.get(), timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue

                # 执行任务
                await self._execute_task(task_id)

            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}", exc_info=True)

        logger.info(f"Worker {worker_id} stopped")

    async def _execute_task(self, task_id: int):
        """
        执行单个任务.

        Args:
            task_id: 任务ID
        """
        db = SessionLocal()
        try:
            # 获取任务
            task = db.query(Task).filter(Task.id == task_id).first()
            if not task:
                logger.error(f"Task {task_id} not found")
                return

            # 检查任务状态
            if task.status != TaskStatus.PENDING:
                logger.warning(f"Task {task_id} status is {task.status}, skipping")
                return

            # 更新任务状态为运行中
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.utcnow()
            db.commit()

            logger.info(f"Executing task {task_id} (type: {task.type})")

            # 根据任务类型分发
            if task.type == TaskType.CRAWL:
                await self._execute_crawl_task(task, db)
            elif task.type == TaskType.REFINE:
                await self._execute_refine_task(task, db)
            else:
                logger.error(f"Unknown task type: {task.type}")
                task.status = TaskStatus.FAILED
                task.error_message = f"Unknown task type: {task.type}"

            db.commit()

        except Exception as e:
            logger.error(f"Task {task_id} execution failed: {e}", exc_info=True)
            # 更新任务状态为失败
            task = db.query(Task).filter(Task.id == task_id).first()
            if task:
                task.status = TaskStatus.FAILED
                task.error_message = str(e)
                task.completed_at = datetime.utcnow()

                # 检查是否需要重试
                if task.retry_count < settings.task_max_retries:
                    task.retry_count += 1
                    task.status = TaskStatus.PENDING
                    logger.info(f"Task {task_id} will retry ({task.retry_count}/{settings.task_max_retries})")
                    # 重新提交任务
                    await self.submit_task(task_id, priority=task.priority)

                db.commit()
        finally:
            db.close()

    async def _execute_crawl_task(self, task: Task, db: Session):
        """
        执行爬取任务.

        Args:
            task: 任务对象
            db: 数据库会话
        """
        try:
            # 调用爬取引擎
            result = await self.crawler_engine.crawl(task, db)

            if result:
                # 任务成功
                task.status = TaskStatus.SUCCESS
                task.completed_at = datetime.utcnow()
                logger.info(f"Crawl task {task.id} completed successfully")

                # 自动创建精炼任务
                await self._create_refine_task(result, task.source_id, db)
            else:
                # 任务失败
                task.status = TaskStatus.FAILED
                task.error_message = "Crawl returned no result"
                task.completed_at = datetime.utcnow()

        except Exception as e:
            logger.error(f"Crawl task {task.id} failed: {e}", exc_info=True)
            raise

    async def _create_refine_task(self, crawl_result, source_id: int, db: Session):
        """
        创建精炼任务.

        Args:
            crawl_result: 爬取结果
            source_id: 信源ID
            db: 数据库会话
        """
        try:
            # 检查是否已存在精炼结果
            from app.models.result import RefinedResult
            existing = db.query(RefinedResult).filter(
                RefinedResult.crawl_result_id == crawl_result.id
            ).first()

            if existing:
                logger.info(f"Refined result already exists for crawl result {crawl_result.id}")
                return

            # 创建精炼任务
            refine_task = Task(
                type=TaskType.REFINE,
                status=TaskStatus.PENDING,
                priority=3,  # 精炼任务优先级较低
                source_id=source_id,
                payload={"crawl_result_id": crawl_result.id},
                created_at=datetime.utcnow(),
            )
            db.add(refine_task)
            db.commit()
            db.refresh(refine_task)

            # 提交到队列
            await self.submit_task(refine_task.id, priority=refine_task.priority)

            logger.info(f"Created refine task {refine_task.id} for crawl result {crawl_result.id}")

        except Exception as e:
            logger.error(f"Failed to create refine task: {e}", exc_info=True)

    async def _execute_refine_task(self, task: Task, db: Session):
        """
        执行精炼任务.

        Args:
            task: 任务对象
            db: 数据库会话
        """
        try:
            # 获取爬取结果ID
            crawl_result_id = task.payload.get("crawl_result_id") if task.payload else None
            if not crawl_result_id:
                logger.error(f"Refine task {task.id} missing crawl_result_id")
                task.status = TaskStatus.FAILED
                task.error_message = "Missing crawl_result_id"
                task.completed_at = datetime.utcnow()
                return

            # 获取爬取结果
            from app.models.result import CrawlResult
            crawl_result = db.query(CrawlResult).filter(
                CrawlResult.id == crawl_result_id
            ).first()

            if not crawl_result:
                logger.error(f"Crawl result {crawl_result_id} not found")
                task.status = TaskStatus.FAILED
                task.error_message = f"Crawl result {crawl_result_id} not found"
                task.completed_at = datetime.utcnow()
                return

            # 调用精炼引擎
            template_name = task.payload.get("template", "summary_keywords") if task.payload else "summary_keywords"
            refined_result = await self.refiner_engine.refine(crawl_result, template_name=template_name)

            if refined_result:
                # 保存精炼结果
                db.add(refined_result)
                db.commit()

                # 任务成功
                task.status = TaskStatus.SUCCESS
                task.completed_at = datetime.utcnow()
                logger.info(f"Refine task {task.id} completed successfully")
            else:
                # 任务失败
                task.status = TaskStatus.FAILED
                task.error_message = "Refine returned no result"
                task.completed_at = datetime.utcnow()

        except Exception as e:
            logger.error(f"Refine task {task.id} failed: {e}", exc_info=True)
            raise

    async def _recover_pending_tasks(self):
        """恢复未完成的任务（进程重启后）."""
        db = SessionLocal()
        try:
            # 查找所有PENDING状态的任务
            pending_tasks = db.query(Task).filter(
                Task.status == TaskStatus.PENDING
            ).all()

            logger.info(f"Recovering {len(pending_tasks)} pending tasks")

            for task in pending_tasks:
                await self.submit_task(task.id, priority=task.priority)

            # 将RUNNING状态的任务重置为PENDING（进程中断导致）
            running_tasks = db.query(Task).filter(
                Task.status == TaskStatus.RUNNING
            ).all()

            for task in running_tasks:
                task.status = TaskStatus.PENDING
                logger.info(f"Reset task {task.id} from RUNNING to PENDING")
                await self.submit_task(task.id, priority=task.priority)

            db.commit()

        except Exception as e:
            logger.error(f"Failed to recover pending tasks: {e}", exc_info=True)
        finally:
            db.close()

    async def _load_scheduled_sources(self):
        """加载所有配置了定时任务的信源."""
        db = SessionLocal()
        try:
            sources = db.query(Source).filter(
                Source.status == SourceStatus.ACTIVE,
                Source.cron_expr.isnot(None)
            ).all()

            logger.info(f"Loading {len(sources)} scheduled sources")

            for source in sources:
                await self.add_scheduled_source(source.id, source.cron_expr)

        except Exception as e:
            logger.error(f"Failed to load scheduled sources: {e}", exc_info=True)
        finally:
            db.close()

    async def add_scheduled_source(self, source_id: int, cron_expr: str):
        """
        添加定时任务.

        Args:
            source_id: 信源ID
            cron_expr: Cron表达式
        """
        try:
            # 如果已存在，先移除
            if source_id in self.scheduled_jobs:
                await self.remove_scheduled_source(source_id)

            # 解析cron表达式
            trigger = CronTrigger.from_crontab(cron_expr)

            # 添加定时任务
            job = self.apscheduler.add_job(
                self._scheduled_crawl_callback,
                trigger=trigger,
                args=[source_id],
                id=f"source_{source_id}",
                replace_existing=True,
            )

            self.scheduled_jobs[source_id] = job.id
            logger.info(f"Added scheduled job for source {source_id}: {cron_expr}")

        except Exception as e:
            logger.error(f"Failed to add scheduled source {source_id}: {e}", exc_info=True)

    async def remove_scheduled_source(self, source_id: int):
        """
        移除定时任务.

        Args:
            source_id: 信源ID
        """
        if source_id in self.scheduled_jobs:
            job_id = self.scheduled_jobs[source_id]
            try:
                self.apscheduler.remove_job(job_id)
                del self.scheduled_jobs[source_id]
                logger.info(f"Removed scheduled job for source {source_id}")
            except Exception as e:
                logger.error(f"Failed to remove scheduled job {job_id}: {e}", exc_info=True)

    async def _scheduled_crawl_callback(self, source_id: int):
        """
        定时任务回调函数.

        Args:
            source_id: 信源ID
        """
        logger.info(f"Scheduled crawl triggered for source {source_id}")

        db = SessionLocal()
        try:
            # 检查信源状态
            source = db.query(Source).filter(Source.id == source_id).first()
            if not source or source.status != SourceStatus.ACTIVE:
                logger.warning(f"Source {source_id} is not active, skipping")
                return

            # 创建爬取任务
            task = Task(
                type=TaskType.CRAWL,
                status=TaskStatus.PENDING,
                priority=5,  # 定时任务优先级中等
                source_id=source.id,
                url=source.url,
                payload={"depth": 0, "scheduled": True},
                created_at=datetime.utcnow(),
            )
            db.add(task)
            db.commit()
            db.refresh(task)

            # 提交到队列
            await self.submit_task(task.id, priority=task.priority)

            logger.info(f"Created scheduled task {task.id} for source {source_id}")

        except Exception as e:
            logger.error(f"Failed to create scheduled task for source {source_id}: {e}", exc_info=True)
        finally:
            db.close()


# 全局调度器实例
_scheduler: Optional[TaskScheduler] = None


def get_scheduler() -> TaskScheduler:
    """获取全局调度器实例."""
    global _scheduler
    if _scheduler is None:
        _scheduler = TaskScheduler()
    return _scheduler
