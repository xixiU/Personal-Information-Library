"""Task API - 任务管理接口."""
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.task import Task, TaskStatus
from app.schemas.task import TaskCreate, TaskResponse
from app.core.scheduler import get_scheduler

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    """创建任务."""
    db_task = Task(**task.model_dump(), status=TaskStatus.PENDING)
    db.add(db_task)
    db.commit()
    db.refresh(db_task)

    # 提交到调度器
    scheduler = get_scheduler()
    await scheduler.submit_task(db_task.id, priority=db_task.priority)

    logger.info(f"Created task: {db_task.id}")
    return db_task


@router.get("", response_model=List[TaskResponse])
async def list_tasks(
    skip: int = 0,
    limit: int = 100,
    status: str = None,
    source_id: int = None,
    db: Session = Depends(get_db),
):
    """获取任务列表."""
    query = db.query(Task)

    if status:
        query = query.filter(Task.status == status)
    if source_id:
        query = query.filter(Task.source_id == source_id)

    tasks = query.order_by(Task.created_at.desc()).offset(skip).limit(limit).all()
    return tasks


@router.get("/stats")
async def get_task_stats(db: Session = Depends(get_db)):
    """获取任务统计."""
    stats = (
        db.query(Task.status, func.count(Task.id))
        .group_by(Task.status)
        .all()
    )

    result = {status: count for status, count in stats}
    return result


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: int, db: Session = Depends(get_db)):
    """获取任务详情."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/{task_id}/cancel", status_code=200)
async def cancel_task(task_id: int, db: Session = Depends(get_db)):
    """取消任务."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status not in [TaskStatus.PENDING, TaskStatus.RUNNING]:
        raise HTTPException(
            status_code=400, detail=f"Cannot cancel task with status {task.status}"
        )

    # TODO: 实现真正的取消逻辑（需要worker支持）
    task.status = TaskStatus.FAILED
    task.error_message = "Cancelled by user"
    db.commit()

    logger.info(f"Cancelled task: {task_id}")
    return {"message": "Task cancelled"}


@router.post("/{task_id}/retry", response_model=TaskResponse)
async def retry_task(task_id: int, db: Session = Depends(get_db)):
    """重试失败的任务."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status != TaskStatus.FAILED:
        raise HTTPException(
            status_code=400, detail=f"Cannot retry task with status {task.status}"
        )

    # 重置任务状态
    task.status = TaskStatus.PENDING
    task.error_message = None
    task.started_at = None
    task.completed_at = None
    db.commit()

    # 重新提交到调度器
    scheduler = get_scheduler()
    await scheduler.submit_task(task.id, priority=task.priority)

    logger.info(f"Retrying task: {task_id}")
    return task
