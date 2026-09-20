"""Source API - 信源管理接口."""
import logging
import xml.etree.ElementTree as ET
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models.source import Source
from app.models.task import Task
from app.models.plugin import Plugin
from app.schemas.source import SourceCreate, SourceUpdate, SourceResponse
from app.core.scheduler import get_scheduler
from app.core.source_config_schema import CONFIG_SCHEMAS

logger = logging.getLogger(__name__)


def _infer_source_type(source: Source, db: Session) -> str:
    """
    兼容旧数据：推断 source_type.

    规则（契约 §1）：
    - plugin 是 RSS 类 → 'rss'
    - crawl_mode == 'full_site' → 'full_site'
    - 否则 → 'single_page'
    """
    if source.source_type:
        return source.source_type

    # 检查 plugin_id 是否为 RSS 插件
    if source.plugin_id:
        plugin = db.query(Plugin).filter(Plugin.id == source.plugin_id).first()
        if plugin and plugin.name == "rss":
            return "rss"

    # 按 crawl_mode 推断
    if source.crawl_mode == "full_site":
        return "full_site"

    return "single_page"


def _apply_source_type_mapping(source_data: dict, db: Session) -> dict:
    """
    将前端的 source_type 映射到后端内部实现.

    source_type → crawl_mode + plugin_id 映射：
    - 'single_page' → crawl_mode='single_page', plugin_id=None (用 GenericPlugin)
    - 'full_site' → crawl_mode='full_site', plugin_id=None (用 GenericPlugin)
    - 'rss' → crawl_mode='single_page', plugin_id=RSS插件ID (RSSPlugin 自带 link discovery)
    """
    source_type = source_data.get("source_type", "single_page")

    if source_type == "rss":
        # 找到 RSS 插件的 ID
        rss_plugin = db.query(Plugin).filter(Plugin.name == "rss", Plugin.enabled == True).first()
        if not rss_plugin:
            logger.warning("RSS plugin not found, falling back to generic")
            source_data["crawl_mode"] = "single_page"
            source_data["plugin_id"] = None
        else:
            source_data["crawl_mode"] = "single_page"  # RSS 插件通过 supports_link_discovery() 触发
            source_data["plugin_id"] = rss_plugin.id
    elif source_type == "full_site":
        source_data["crawl_mode"] = "full_site"
        source_data["plugin_id"] = None  # 使用 GenericPlugin
    else:  # single_page
        source_data["crawl_mode"] = "single_page"
        source_data["plugin_id"] = None  # 使用 GenericPlugin

    return source_data

router = APIRouter(prefix="/api/sources", tags=["sources"])


# ============================================================================
# 静态路径路由（必须在动态路由 /{source_id} 之前注册）
# ============================================================================

@router.get("/config-schema")
async def get_config_schema(source_type: str):
    """
    获取配置项 Schema（契约 §2）.

    前端根据 source_type 拉取字段定义，动态渲染表单。
    """
    if source_type not in CONFIG_SCHEMAS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown source_type: {source_type}. Must be one of: single_page, full_site, rss"
        )

    return CONFIG_SCHEMAS[source_type]


# 批量导入相关 Schema
class BatchImportRequest(BaseModel):
    """批量导入请求（契约 §3）."""
    import_type: str  # 'opml' | 'url_list'
    data: str | List[str]  # opml: XML 字符串; url_list: URL 数组
    default_category_id: int | None = None
    default_config: dict | None = None
    default_cron_expr: str | None = None


class ImportDetail(BaseModel):
    """单条导入结果."""
    name: str
    url: str
    status: str  # 'success' | 'failed' | 'skipped'
    reason: str = ""


class BatchImportResponse(BaseModel):
    """批量导入响应."""
    success_count: int
    failed_count: int
    skipped_count: int
    details: List[ImportDetail]


def _parse_opml(opml_xml: str) -> List[dict]:
    """
    解析 OPML XML，提取订阅源信息.

    Returns:
        [{"name": "xxx", "url": "https://...", "category": "xxx"}, ...]
    """
    try:
        root = ET.fromstring(opml_xml)
        feeds = []

        # 遍历所有 outline 元素
        for outline in root.iter("outline"):
            # RSS feed 一般有 xmlUrl 属性
            xml_url = outline.get("xmlUrl")
            if xml_url:
                title = outline.get("title") or outline.get("text") or xml_url
                category = outline.get("category") or ""
                feeds.append({
                    "name": title,
                    "url": xml_url,
                    "category": category,
                })

        return feeds

    except ET.ParseError as e:
        logger.error(f"OPML parse error: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid OPML format: {e}")


@router.post("/batch-import", response_model=BatchImportResponse)
async def batch_import_sources(request: BatchImportRequest, db: Session = Depends(get_db)):
    """
    批量导入信源（契约 §3）.

    支持两种导入方式：
    1. import_type='opml': 传入 OPML XML 字符串
    2. import_type='url_list': 传入 URL 字符串数组

    所有导入的信源 source_type 均为 'rss'。
    """
    if request.import_type not in ["opml", "url_list"]:
        raise HTTPException(
            status_code=400,
            detail="import_type must be 'opml' or 'url_list'"
        )

    # 解析导入数据
    feeds = []
    if request.import_type == "opml":
        if not isinstance(request.data, str):
            raise HTTPException(status_code=400, detail="data must be XML string for OPML import")
        feeds = _parse_opml(request.data)
    else:  # url_list
        if not isinstance(request.data, list):
            raise HTTPException(status_code=400, detail="data must be array of URLs for url_list import")
        feeds = [{"name": url, "url": url, "category": ""} for url in request.data]

    # 批量创建
    success_count = 0
    failed_count = 0
    skipped_count = 0
    details = []

    for feed in feeds:
        url = feed["url"]
        name = feed["name"]

        try:
            # URL 去重检查
            existing = db.query(Source).filter(Source.url == url).first()
            if existing:
                skipped_count += 1
                details.append(ImportDetail(
                    name=name,
                    url=url,
                    status="skipped",
                    reason="URL 已存在"
                ))
                continue

            # 准备创建数据
            source_data = {
                "name": name,
                "url": url,
                "source_type": "rss",
                "config": request.default_config or {},
                "cron_expr": request.default_cron_expr,
                "category_id": request.default_category_id,
                "status": "active",
            }

            # 应用 source_type 映射
            source_data = _apply_source_type_mapping(source_data, db)

            # 创建信源
            db_source = Source(**source_data)
            db.add(db_source)
            db.flush()  # 获取 ID，但不提交

            success_count += 1
            details.append(ImportDetail(
                name=name,
                url=url,
                status="success",
                reason=""
            ))

        except Exception as e:
            failed_count += 1
            details.append(ImportDetail(
                name=name,
                url=url,
                status="failed",
                reason=str(e)
            ))
            logger.error(f"Failed to import {url}: {e}")

    # 提交所有成功的导入
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Batch import commit failed: {e}")
        raise HTTPException(status_code=500, detail="Database commit failed")

    logger.info(f"Batch import completed: {success_count} success, {failed_count} failed, {skipped_count} skipped")

    return BatchImportResponse(
        success_count=success_count,
        failed_count=failed_count,
        skipped_count=skipped_count,
        details=details
    )


# ============================================================================
# 基础 CRUD 路由
# ============================================================================

@router.post("", response_model=SourceResponse, status_code=201)
async def create_source(source: SourceCreate, db: Session = Depends(get_db)):
    """创建信源."""
    # 检查URL是否已存在
    existing = db.query(Source).filter(Source.url == source.url).first()
    if existing:
        raise HTTPException(status_code=400, detail="URL already exists")

    # 应用 source_type 映射到内部实现
    source_data = source.model_dump()
    source_data = _apply_source_type_mapping(source_data, db)

    # 创建信源
    db_source = Source(**source_data)
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

    # 兼容处理：推断 source_type
    for source in sources:
        if not source.source_type:
            source.source_type = _infer_source_type(source, db)

    return sources


@router.get("/{source_id}", response_model=SourceResponse)
async def get_source(source_id: int, db: Session = Depends(get_db)):
    """获取信源详情."""
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    # 兼容处理：推断 source_type
    if not source.source_type:
        source.source_type = _infer_source_type(source, db)

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

    # 如果更新了 source_type，需要重新映射
    if "source_type" in update_data:
        update_data = _apply_source_type_mapping(update_data, db)

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

