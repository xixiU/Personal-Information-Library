"""Dashboard API - 仪表盘统计接口（契约 §4）."""
import logging
from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models.source import Source
from app.models.task import Task, TaskStatus
from app.models.result import CrawlResult, RefinedResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


class RecentResult(BaseModel):
    """最近的精炼结果."""
    id: int
    title: str
    summary: str
    quality_score: int | None
    created_at: datetime


class DashboardStats(BaseModel):
    """仪表盘统计数据."""
    sources: dict  # {"total": int, "today": int}
    tasks: dict  # {"pending": int, "running": int, "success": int, "failed": int}
    results: dict  # {"total": int, "today": int, "avg_quality_score": float}
    recent_results: List[RecentResult]


def _get_today_start() -> datetime:
    """获取今天零点（UTC+8）."""
    # 工程约定 UTC+8
    now_utc = datetime.utcnow()
    # UTC+8 的今天零点对应的 UTC 时间
    utc8_now = now_utc + timedelta(hours=8)
    utc8_today_start = utc8_now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_start_utc = utc8_today_start - timedelta(hours=8)
    return today_start_utc


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """
    获取仪表盘统计数据（契约 §4）.

    返回信源、任务、精炼结果的统计信息，以及最近 5 条精炼结果。
    """
    today_start = _get_today_start()

    # 1. 信源统计
    sources_total = db.query(Source).count()
    sources_today = db.query(Source).filter(Source.created_at >= today_start).count()

    # 2. 任务统计
    tasks_pending = db.query(Task).filter(Task.status == TaskStatus.PENDING).count()
    tasks_running = db.query(Task).filter(Task.status == TaskStatus.RUNNING).count()
    tasks_success = db.query(Task).filter(Task.status == TaskStatus.SUCCESS).count()
    tasks_failed = db.query(Task).filter(Task.status == TaskStatus.FAILED).count()

    # 3. 精炼结果统计
    results_total = db.query(RefinedResult).count()
    results_today = db.query(RefinedResult).filter(RefinedResult.created_at >= today_start).count()

    # 平均质量分
    avg_score_result = db.query(func.avg(RefinedResult.quality_score)).filter(
        RefinedResult.quality_score.isnot(None)
    ).scalar()
    avg_quality_score = round(float(avg_score_result), 1) if avg_score_result else 0.0

    # 4. 最近 5 条精炼结果
    recent_refined = (
        db.query(RefinedResult, CrawlResult.title)
        .join(CrawlResult, RefinedResult.crawl_result_id == CrawlResult.id)
        .order_by(RefinedResult.created_at.desc())
        .limit(5)
        .all()
    )

    recent_results = []
    for refined, title in recent_refined:
        recent_results.append(RecentResult(
            id=refined.id,
            title=title or "无标题",
            summary=refined.summary or "",
            quality_score=refined.quality_score,
            created_at=refined.created_at
        ))

    return DashboardStats(
        sources={
            "total": sources_total,
            "today": sources_today,
        },
        tasks={
            "pending": tasks_pending,
            "running": tasks_running,
            "success": tasks_success,
            "failed": tasks_failed,
        },
        results={
            "total": results_total,
            "today": results_today,
            "avg_quality_score": avg_quality_score,
        },
        recent_results=recent_results
    )
