"""Result API - 结果查询接口."""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from datetime import datetime

from app.database import get_db
from app.models.result import CrawlResult, RefinedResult
from app.schemas.result import (
    CrawlResultResponse,
    RefinedResultResponse,
    MarkReadRequest,
    ArchiveRequest,
)
from app.schemas.highlight import HighlightResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/results", tags=["results"])


@router.get("/crawl", response_model=List[CrawlResultResponse])
async def list_crawl_results(
    skip: int = 0,
    limit: int = 100,
    source_id: int = None,
    db: Session = Depends(get_db),
):
    """获取爬取结果列表."""
    query = db.query(CrawlResult)

    if source_id:
        query = query.filter(CrawlResult.source_id == source_id)

    results = query.order_by(CrawlResult.created_at.desc()).offset(skip).limit(limit).all()
    return results


@router.get("/crawl/{result_id}", response_model=CrawlResultResponse)
async def get_crawl_result(result_id: int, db: Session = Depends(get_db)):
    """获取爬取结果详情."""
    result = db.query(CrawlResult).filter(CrawlResult.id == result_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Crawl result not found")
    return result


@router.get("/refine", response_model=List[RefinedResultResponse])
async def list_refined_results(
    skip: int = 0,
    limit: int = 100,
    min_score: Optional[int] = Query(None, ge=0, le=100),
    max_score: Optional[int] = Query(None, ge=0, le=100),
    is_read: Optional[bool] = Query(None),
    is_archived: Optional[bool] = Query(False),
    order_by: Optional[str] = Query(None, pattern="^(quality_score|interest_score|created_at)$"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
):
    """获取精炼结果列表（B2：默认按兴趣分排序；任务 E：支持已读/归档过滤）."""
    query = db.query(RefinedResult)

    # 分数过滤需同时保留 quality_score 为 NULL 的记录（未评分内容也应可见）
    if min_score is not None:
        query = query.filter(
            (RefinedResult.quality_score >= min_score) | (RefinedResult.quality_score.is_(None))
        )
    if max_score is not None:
        query = query.filter(
            (RefinedResult.quality_score <= max_score) | (RefinedResult.quality_score.is_(None))
        )

    # 任务 E：已读/归档过滤
    # is_read: True/False 显式过滤，None 显示全部
    if is_read is not None:
        query = query.filter(RefinedResult.is_read == is_read)
    # is_archived: 默认 False（不显示已归档），显式传 True 显示归档箱，传 None 显示全部
    if is_archived is not None:
        query = query.filter(RefinedResult.is_archived == is_archived)

    # 排序（B2：默认按兴趣分 DESC NULLS LAST，再按创建时间 DESC）
    if order_by is None:
        # 默认排序：兴趣分高的在前，NULL 在后，同分按创建时间倒序
        results = (
            query.order_by(
                RefinedResult.interest_score.desc().nullslast(),
                RefinedResult.created_at.desc()
            )
            .offset(skip)
            .limit(limit)
            .all()
        )
    else:
        # 显式指定排序字段
        sort_column = RefinedResult.created_at
        if order_by == "quality_score":
            sort_column = RefinedResult.quality_score
        elif order_by == "interest_score":
            sort_column = RefinedResult.interest_score

        if order == "asc":
            results = query.order_by(sort_column.asc().nullslast()).offset(skip).limit(limit).all()
        else:
            results = query.order_by(sort_column.desc().nullslast()).offset(skip).limit(limit).all()

    # 批量统计高亮数量，避免 N+1（一条 GROUP BY 查询覆盖本页所有结果）
    if results:
        from sqlalchemy import func
        from app.models.highlight import Highlight

        result_ids = [r.id for r in results]
        count_rows = (
            db.query(Highlight.refined_result_id, func.count(Highlight.id))
            .filter(Highlight.refined_result_id.in_(result_ids))
            .group_by(Highlight.refined_result_id)
            .all()
        )
        count_map = {rid: cnt for rid, cnt in count_rows}
        for r in results:
            # 动态附加属性，供 RefinedResultResponse(from_attributes) 读取
            r.highlight_count = count_map.get(r.id, 0)

    return results


@router.get("/refine/{result_id}", response_model=RefinedResultResponse)
async def get_refined_result(result_id: int, db: Session = Depends(get_db)):
    """获取精炼结果详情."""
    result = db.query(RefinedResult).filter(RefinedResult.id == result_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Refined result not found")
    return result


@router.get("/refine/{result_id}/highlights", response_model=List[HighlightResponse])
async def list_result_highlights(result_id: int, db: Session = Depends(get_db)):
    """列出某个精炼结果的所有高亮（任务 D）."""
    result = db.query(RefinedResult).filter(RefinedResult.id == result_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="精炼结果不存在")

    from app.api.highlights import list_highlights_by_result
    return list_highlights_by_result(result_id, db)


@router.post("/refine/{result_id}/mark-read", response_model=RefinedResultResponse)
async def mark_read(
    result_id: int, data: MarkReadRequest, db: Session = Depends(get_db)
):
    """标记已读/未读（任务 E）."""
    result = db.query(RefinedResult).filter(RefinedResult.id == result_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="精炼结果不存在")

    result.is_read = data.is_read
    # 标记已读时记录时间，取消已读时清空
    result.read_at = datetime.utcnow() if data.is_read else None
    db.commit()
    db.refresh(result)
    return result


@router.post("/refine/{result_id}/archive", response_model=RefinedResultResponse)
async def archive_result(
    result_id: int, data: ArchiveRequest, db: Session = Depends(get_db)
):
    """归档/取消归档（任务 E）."""
    result = db.query(RefinedResult).filter(RefinedResult.id == result_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="精炼结果不存在")

    result.is_archived = data.is_archived
    db.commit()
    db.refresh(result)
    return result
