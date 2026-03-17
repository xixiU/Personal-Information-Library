"""NotificationEngine - 通知引擎，评估规则并触发通知."""
import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Type

from sqlalchemy.orm import Session

from app.models.notification import NotificationChannel, NotificationRule, NotificationLog
from app.models.result import CrawlResult, RefinedResult
from app.models.task import Task
from app.models.source import Source
from app.core.notifiers.base import BaseNotifier, NotificationMessage, BatchNotificationMessage
from app.core.notifiers.webhook import WebhookNotifier
from app.core.notifiers.telegram import TelegramNotifier
from app.core.notifiers.feishu import FeishuNotifier

logger = logging.getLogger(__name__)


class NotificationEngine:
    """通知引擎，精炼完成后评估规则并触发通知."""

    NOTIFIER_MAP: Dict[str, Type[BaseNotifier]] = {
        "webhook": WebhookNotifier,
        "telegram": TelegramNotifier,
        "feishu": FeishuNotifier,
    }

    def __init__(self, scheduler=None):
        self.scheduler = scheduler  # APScheduler instance
        self._active_batch_jobs: Dict[int, str] = {}  # rule_id -> batch_id

    async def evaluate(self, refined_result: RefinedResult, db: Session):
        """精炼完成后调用，评估并触发通知."""
        category_id = self._get_category_id(refined_result, db)
        if not category_id:
            return

        rules = (
            db.query(NotificationRule)
            .filter(
                NotificationRule.category_id == category_id,
                NotificationRule.enabled == True,
                NotificationRule.channel.has(NotificationChannel.enabled == True),
            )
            .all()
        )

        for rule in rules:
            try:
                if not self._match_conditions(rule, refined_result):
                    continue

                # 去重
                exists = (
                    db.query(NotificationLog)
                    .filter(
                        NotificationLog.rule_id == rule.id,
                        NotificationLog.refined_result_id == refined_result.id,
                    )
                    .first()
                )
                if exists:
                    continue

                if rule.notify_mode == "instant":
                    await self._send_instant(rule, refined_result, db)
                elif rule.notify_mode == "batch":
                    await self._enqueue_batch(rule, refined_result, db)
            except Exception as e:
                logger.error(f"Failed to process rule {rule.id}: {e}", exc_info=True)

    def _get_category_id(self, refined_result: RefinedResult, db: Session) -> Optional[int]:
        """通过 refined_result -> crawl_result -> task -> source -> category_id."""
        crawl_result = db.query(CrawlResult).filter(
            CrawlResult.id == refined_result.crawl_result_id
        ).first()
        if not crawl_result:
            return None

        task = db.query(Task).filter(Task.id == crawl_result.task_id).first()
        if not task or not task.source_id:
            return None

        source = db.query(Source).filter(Source.id == task.source_id).first()
        if not source or not source.category_id:
            return None

        return source.category_id

    def _match_conditions(self, rule: NotificationRule, result: RefinedResult) -> bool:
        """评估触发条件."""
        conditions = rule.conditions or {}

        # 质量阈值
        min_score = conditions.get("min_quality_score")
        if min_score is not None:
            if result.quality_score is None or result.quality_score < min_score:
                return False

        # 关键词匹配
        keywords = conditions.get("keywords")
        if keywords:
            # keywords 可能是 list 或 JSON string
            result_kw = result.keywords or []
            if isinstance(result_kw, list):
                result_kw_str = " ".join(result_kw).lower()
            else:
                result_kw_str = str(result_kw).lower()
            result_summary = (result.summary or "").lower()
            if not any(
                kw.lower() in result_kw_str or kw.lower() in result_summary
                for kw in keywords
            ):
                return False

        return True

    async def _send_instant(self, rule: NotificationRule, refined_result: RefinedResult, db: Session):
        """即时发送."""
        notifier = self._get_notifier(rule.channel)
        if not notifier:
            return

        message = self._build_message(refined_result, rule, db)
        success = await notifier.send(message)

        log = NotificationLog(
            rule_id=rule.id,
            channel_id=rule.channel_id,
            refined_result_id=refined_result.id,
            status="success" if success else "failed",
            sent_at=datetime.utcnow() if success else None,
            created_at=datetime.utcnow(),
        )
        db.add(log)
        db.commit()

        if success:
            logger.info(f"Instant notification sent for rule {rule.id}, result {refined_result.id}")
        else:
            logger.warning(f"Instant notification failed for rule {rule.id}, result {refined_result.id}")

    async def _enqueue_batch(self, rule: NotificationRule, refined_result: RefinedResult, db: Session):
        """聚合入队."""
        batch_id = self._active_batch_jobs.get(rule.id)
        if not batch_id:
            batch_id = str(uuid.uuid4())
            self._active_batch_jobs[rule.id] = batch_id

        log = NotificationLog(
            rule_id=rule.id,
            channel_id=rule.channel_id,
            refined_result_id=refined_result.id,
            batch_id=batch_id,
            status="pending",
            created_at=datetime.utcnow(),
        )
        db.add(log)
        db.commit()

        # 检查是否达到数量上限
        batch_max = (rule.conditions or {}).get("batch_max_count", 10)
        pending_count = (
            db.query(NotificationLog)
            .filter(
                NotificationLog.rule_id == rule.id,
                NotificationLog.batch_id == batch_id,
                NotificationLog.status == "pending",
            )
            .count()
        )

        if pending_count >= batch_max:
            await self._flush_batch(rule.id, batch_id, db)
        elif self.scheduler:
            batch_window = (rule.conditions or {}).get("batch_window", 1800)
            job_id = f"batch_{rule.id}_{batch_id}"
            try:
                self.scheduler.add_job(
                    self._flush_batch_job,
                    trigger="date",
                    run_date=datetime.utcnow() + timedelta(seconds=batch_window),
                    args=[rule.id, batch_id],
                    id=job_id,
                    replace_existing=True,
                )
            except Exception as e:
                logger.warning(f"Failed to schedule batch job: {e}")

    async def _flush_batch(self, rule_id: int, batch_id: str, db: Session):
        """执行聚合发送."""
        logs = (
            db.query(NotificationLog)
            .filter(
                NotificationLog.rule_id == rule_id,
                NotificationLog.batch_id == batch_id,
                NotificationLog.status == "pending",
            )
            .all()
        )

        if not logs:
            return

        rule = db.query(NotificationRule).filter(NotificationRule.id == rule_id).first()
        if not rule:
            return

        notifier = self._get_notifier(rule.channel)
        if not notifier:
            return

        items = []
        for log in logs:
            result = db.query(RefinedResult).filter(
                RefinedResult.id == log.refined_result_id
            ).first()
            if result:
                items.append(self._build_message(result, rule, db))

        batch_msg = BatchNotificationMessage(
            category_name=rule.category.name if rule.category else "未分类",
            items=items,
            total_count=len(items),
        )

        success = await notifier.send_batch(batch_msg)

        now = datetime.utcnow()
        for log in logs:
            log.status = "success" if success else "failed"
            log.sent_at = now if success else None
        db.commit()

        # 清理 batch 状态
        self._active_batch_jobs.pop(rule_id, None)

        if success:
            logger.info(f"Batch notification sent for rule {rule_id}, {len(items)} items")

    async def _flush_batch_job(self, rule_id: int, batch_id: str):
        """APScheduler 回调，创建新 session 执行 flush."""
        from app.database import SessionLocal
        db = SessionLocal()
        try:
            await self._flush_batch(rule_id, batch_id, db)
        except Exception as e:
            logger.error(f"Batch flush job failed: {e}", exc_info=True)
        finally:
            db.close()

    def _get_notifier(self, channel: NotificationChannel) -> Optional[BaseNotifier]:
        """根据渠道类型获取 notifier 实例."""
        cls = self.NOTIFIER_MAP.get(channel.channel_type)
        if not cls:
            logger.error(f"Unknown channel type: {channel.channel_type}")
            return None
        return cls(channel.config or {})

    def _build_message(
        self, refined_result: RefinedResult, rule: NotificationRule, db: Session
    ) -> NotificationMessage:
        """构建通知消息."""
        # 获取原始 crawl_result 信息
        crawl_result = db.query(CrawlResult).filter(
            CrawlResult.id == refined_result.crawl_result_id
        ).first()

        # 获取 source 名称
        source_name = "未知信源"
        category_name = "未分类"
        if crawl_result:
            task = db.query(Task).filter(Task.id == crawl_result.task_id).first()
            if task and task.source_id:
                source = db.query(Source).filter(Source.id == task.source_id).first()
                if source:
                    source_name = source.name

        if rule.category:
            category_name = rule.category.name

        keywords = refined_result.keywords or []
        if isinstance(keywords, str):
            keywords = [keywords]

        return NotificationMessage(
            title=crawl_result.title if crawl_result else "无标题",
            summary=refined_result.summary or "",
            url=crawl_result.url if crawl_result else "",
            quality_score=refined_result.quality_score,
            keywords=keywords,
            category_name=category_name,
            source_name=source_name,
            timestamp=refined_result.created_at.isoformat() if refined_result.created_at else "",
        )
