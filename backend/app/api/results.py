"""Result API - 结果查询接口."""
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.result import CrawlResult, RefinedResult
from app.schemas.result import CrawlResultResponse, RefinedResultResponse

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
    db: Session = Depends(get_db),
):
    """获取精炼结果列表."""
    results = (
        db.query(RefinedResult)
        .order_by(RefinedResult.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return results


@router.get("/refine/{result_id}", response_model=RefinedResultResponse)
async def get_refined_result(result_id: int, db: Session = Depends(get_db)):
    """获取精炼结果详情."""
    result = db.query(RefinedResult).filter(RefinedResult.id == result_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Refined result not found")
    return result
