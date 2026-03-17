"""Refine API - 精炼管理接口."""
import logging
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.result import CrawlResult, RefinedResult
from app.models.task import Task
from app.core.refiner import RefinerEngine
from app.core.scheduler import get_scheduler

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/refine", tags=["refine"])


@router.post("/{crawl_result_id}", status_code=202)
async def trigger_refine(
    crawl_result_id: int,
    template: str = "summary_keywords",
    db: Session = Depends(get_db),
):
    """手动触发精炼."""
    # 检查爬取结果是否存在
    crawl_result = db.query(CrawlResult).filter(CrawlResult.id == crawl_result_id).first()
    if not crawl_result:
        raise HTTPException(status_code=404, detail="Crawl result not found")

    # 检查是否已存在精炼结果
    existing = db.query(RefinedResult).filter(
        RefinedResult.crawl_result_id == crawl_result_id
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Refined result already exists")

    # 创建精炼任务
    task = Task(
        type="refine",
        status="pending",
        priority=10,  # 手动触发的任务优先级较高
        source_id=crawl_result.source_id,
        payload={"crawl_result_id": crawl_result_id, "template": template},
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    # 提交到调度器
    scheduler = get_scheduler()
    await scheduler.submit_task(task.id, priority=task.priority)

    logger.info(f"Triggered refine for crawl result {crawl_result_id}, task {task.id}")
    return {"task_id": task.id, "message": "Refine task created"}


@router.get("/templates")
async def get_templates():
    """获取精炼模板列表."""
    templates = RefinerEngine.get_templates()

    # 格式化返回
    result = []
    for key, template in templates.items():
        result.append({
            "key": key,
            "name": template["name"],
            "system": template["system"],
            "user_template": template["user"],
        })

    return result


@router.post("/templates", status_code=201)
async def create_template(
    name: str,
    system: str,
    user: str,
    description: str = "",
):
    """创建自定义模板."""
    # 检查模板名称是否已存在
    templates = RefinerEngine.get_templates()
    if name in templates:
        raise HTTPException(status_code=400, detail="Template name already exists")

    # 添加模板
    RefinerEngine.add_template(name, system, user, description)

    logger.info(f"Created custom template: {name}")
    return {
        "name": name,
        "message": "Template created successfully",
    }


@router.get("/preview/{crawl_result_id}")
async def preview_refine(
    crawl_result_id: int,
    template: str = "summary_keywords",
    db: Session = Depends(get_db),
):
    """预览精炼结果（不保存）."""
    # 检查爬取结果是否存在
    crawl_result = db.query(CrawlResult).filter(CrawlResult.id == crawl_result_id).first()
    if not crawl_result:
        raise HTTPException(status_code=404, detail="Crawl result not found")

    # 执行精炼（不保存）
    refiner = RefinerEngine()
    refined_result = await refiner.refine(crawl_result, template_name=template, db=db)

    if not refined_result:
        raise HTTPException(status_code=500, detail="Refine failed")

    return {
        "summary": refined_result.summary,
        "keywords": refined_result.keywords,
        "category": refined_result.category,
        "meta_data": refined_result.meta_data,
    }
