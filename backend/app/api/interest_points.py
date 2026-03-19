"""InterestPoint API - 兴趣点管理接口."""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.interest import InterestPoint, UserFeedback
from app.models.result import RefinedResult
from app.models.category import Category
from app.schemas.interest import (
    InterestPointCreate,
    InterestPointUpdate,
    InterestPointResponse,
    CategoryBrief,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/interest-points", tags=["interest-points"])


def _enrich_with_category(point: InterestPoint, db: Session) -> dict:
    """为兴趣点附加分类简要信息."""
    data = {c.name: getattr(point, c.name) for c in point.__table__.columns}
    if point.category_id:
        cat = db.query(Category).filter(Category.id == point.category_id).first()
        if cat:
            data["category"] = CategoryBrief.model_validate(cat)
    return data


@router.get("/stats")
async def interest_point_stats(db: Session = Depends(get_db)):
    """兴趣点统计（词云数据）."""
    points = (
        db.query(InterestPoint)
        .filter(InterestPoint.is_active == True)  # noqa: E712
        .all()
    )

    result = []
    for point in points:
        # 统计该兴趣点关键词命中的正向反馈数量
        feedback_count = 0
        if point.keywords:
            # 查找 keywords 与该兴趣点有交集的 RefinedResult
            all_results = db.query(RefinedResult).filter(RefinedResult.keywords.isnot(None)).all()
            matched_result_ids = []
            for r in all_results:
                if r.keywords and set(r.keywords) & set(point.keywords):
                    matched_result_ids.append(r.id)

            if matched_result_ids:
                feedback_count = (
                    db.query(UserFeedback)
                    .filter(
                        UserFeedback.refined_result_id.in_(matched_result_ids),
                        UserFeedback.action.in_(["like", "collect"]),
                    )
                    .count()
                )

        result.append({
            "name": point.name,
            "weight": point.weight,
            "source": point.source,
            "is_active": point.is_active,
            "keyword_count": len(point.keywords) if point.keywords else 0,
            "feedback_count": feedback_count,
        })

    return result


@router.post("", response_model=InterestPointResponse, status_code=201)
async def create_interest_point(
    payload: InterestPointCreate, db: Session = Depends(get_db)
):
    """创建兴趣点（source=manual）."""
    existing = db.query(InterestPoint).filter(InterestPoint.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=409, detail="兴趣点名称已存在")

    db_point = InterestPoint(**payload.model_dump(), source="manual")
    db.add(db_point)
    db.commit()
    db.refresh(db_point)

    logger.info(f"Created interest point: {db_point.id} ({db_point.name})")
    return _enrich_with_category(db_point, db)


@router.get("", response_model=List[InterestPointResponse])
async def list_interest_points(
    is_active: Optional[bool] = Query(None),
    source: Optional[str] = Query(None),
    category_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """兴趣点列表（支持筛选）."""
    query = db.query(InterestPoint)
    if is_active is not None:
        query = query.filter(InterestPoint.is_active == is_active)
    if source is not None:
        query = query.filter(InterestPoint.source == source)
    if category_id is not None:
        query = query.filter(InterestPoint.category_id == category_id)

    points = query.order_by(InterestPoint.weight.desc()).all()
    return [_enrich_with_category(p, db) for p in points]


@router.get("/{point_id}", response_model=InterestPointResponse)
async def get_interest_point(point_id: int, db: Session = Depends(get_db)):
    """获取兴趣点详情."""
    point = db.query(InterestPoint).filter(InterestPoint.id == point_id).first()
    if not point:
        raise HTTPException(status_code=404, detail="InterestPoint not found")
    return _enrich_with_category(point, db)


@router.put("/{point_id}", response_model=InterestPointResponse)
async def update_interest_point(
    point_id: int, payload: InterestPointUpdate, db: Session = Depends(get_db)
):
    """更新兴趣点."""
    point = db.query(InterestPoint).filter(InterestPoint.id == point_id).first()
    if not point:
        raise HTTPException(status_code=404, detail="InterestPoint not found")

    update_data = payload.model_dump(exclude_unset=True)

    # 名称唯一性检查
    if "name" in update_data:
        existing = (
            db.query(InterestPoint)
            .filter(InterestPoint.name == update_data["name"], InterestPoint.id != point_id)
            .first()
        )
        if existing:
            raise HTTPException(status_code=409, detail="兴趣点名称已存在")

    for field, value in update_data.items():
        setattr(point, field, value)

    db.commit()
    db.refresh(point)

    logger.info(f"Updated interest point: {point_id}")
    return _enrich_with_category(point, db)


@router.delete("/{point_id}", status_code=204)
async def delete_interest_point(point_id: int, db: Session = Depends(get_db)):
    """删除兴趣点."""
    point = db.query(InterestPoint).filter(InterestPoint.id == point_id).first()
    if not point:
        raise HTTPException(status_code=404, detail="InterestPoint not found")

    db.delete(point)
    db.commit()

    logger.info(f"Deleted interest point: {point_id}")
    return None


@router.post("/{point_id}/activate", response_model=InterestPointResponse)
async def activate_interest_point(point_id: int, db: Session = Depends(get_db)):
    """启用兴趣点."""
    point = db.query(InterestPoint).filter(InterestPoint.id == point_id).first()
    if not point:
        raise HTTPException(status_code=404, detail="InterestPoint not found")

    point.is_active = True
    db.commit()
    db.refresh(point)

    logger.info(f"Activated interest point: {point_id}")
    return _enrich_with_category(point, db)


@router.post("/{point_id}/deactivate", response_model=InterestPointResponse)
async def deactivate_interest_point(point_id: int, db: Session = Depends(get_db)):
    """禁用兴趣点."""
    point = db.query(InterestPoint).filter(InterestPoint.id == point_id).first()
    if not point:
        raise HTTPException(status_code=404, detail="InterestPoint not found")

    point.is_active = False
    db.commit()
    db.refresh(point)

    logger.info(f"Deactivated interest point: {point_id}")
    return _enrich_with_category(point, db)
