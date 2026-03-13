"""Source API - 信源管理接口."""
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.source import Source
from app.models.task import Task
from app.schemas.source import SourceCreate, SourceUpdate, SourceResponse
from app.core.scheduler import get_scheduler

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sources", tags=["sources"])


@router.post("", response_model=SourceResponse, status_code=201)
async def create_source(source: SourceCreate, db: Session = Depends(get_db)):
    """创建信源."""
    # 检查URL是否已存在
    existing = db.query(Source).filter(Source.url == source.url).first()
    if existing:
        raise HTTPException(status_code=400, detail="URL already exists")

    # 创建信源
    db_source = Source(**source.model_dump())
    db.add(db_source)
    db.commit()
    db.refresh(db_source)

    logger.info(f"Created source: {db_source.id}")
    return db_source


@router.get("", response_model=List[SourceResponse])
async def list_sources(
    skip: int = 0,
    limit: int = 100,
    status: str = None,
    db: Session = Depends(get_db),
):
    """获取信源列表."""
    query = db.query(Source)

    if status:
        query = query.filter(Source.status == status)

    sources = query.offset(skip).limit(limit).all()
    return sources


@router.get("/{source_id}", response_model=SourceResponse)
async def get_source(source_id: int, db: Session = Depends(get_db)):
    """获取信源详情."""
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return source


@router.put("/{source_id}", response_model=SourceResponse)
async def update_source(
    source_id: int, source_update: SourceUpdate, db: Session = Depends(get_db)
):
    """更新信源."""
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    # 更新字段
    update_data = source_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(source, field, value)

    db.commit()
    db.refresh(source)

    logger.info(f"Updated source: {source_id}")
    return source


@router.delete("/{source_id}", status_code=204)
async def delete_source(source_id: int, db: Session = Depends(get_db)):
    """删除信源."""
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    db.delete(source)
    db.commit()

    logger.info(f"Deleted source: {source_id}")
    return None


@router.post("/{source_id}/trigger", status_code=202)
async def trigger_crawl(source_id: int, db: Session = Depends(get_db)):
    """手动触发爬取."""
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    # 创建爬取任务
    task = Task(
        type="crawl",
        status="pending",
        priority=10,  # 手动触发的任务优先级较高
        source_id=source.id,
        url=source.url,
        payload={"depth": 0, "manual": True},
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    # 提交到调度器
    scheduler = get_scheduler()
    await scheduler.submit_task(task.id, priority=task.priority)

    logger.info(f"Triggered crawl for source {source_id}, task {task.id}")
    return {"task_id": task.id, "message": "Crawl task created"}


@router.post("/{source_id}/schedule", status_code=200)
async def add_schedule(
    source_id: int,
    cron_expr: str = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """添加或更新定时任务."""
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    # 更新cron表达式
    source.cron_expr = cron_expr
    db.commit()

    # 添加到调度器
    scheduler = get_scheduler()
    await scheduler.add_scheduled_source(source.id, cron_expr)

    logger.info(f"Added schedule for source {source_id}: {cron_expr}")
    return {"message": "Schedule added", "cron_expr": cron_expr}


@router.delete("/{source_id}/schedule", status_code=200)
async def remove_schedule(source_id: int, db: Session = Depends(get_db)):
    """移除定时任务."""
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    # 清除cron表达式
    source.cron_expr = None
    db.commit()

    # 从调度器移除
    scheduler = get_scheduler()
    await scheduler.remove_scheduled_source(source.id)

    logger.info(f"Removed schedule for source {source_id}")
    return {"message": "Schedule removed"}


@router.get("/{source_id}/schedule")
async def get_schedule(source_id: int, db: Session = Depends(get_db)):
    """获取定时任务配置."""
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    return {
        "source_id": source.id,
        "cron_expr": source.cron_expr,
        "has_schedule": source.cron_expr is not None,
    }
