"""Interest Discovery API - AI 发现兴趣点接口."""
import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.interest_discoverer import InterestDiscoverer
from app.schemas.interest import InterestPointResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/interest-points", tags=["interest-discovery"])


@router.post("/discover", response_model=List[InterestPointResponse])
async def discover_interest_points(
    days: int = Query(default=30, ge=1, le=365),
    category_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
):
    """手动触发 AI 发现兴趣点."""
    discoverer = InterestDiscoverer()
    try:
        points = await discoverer.discover(db, days=days, category_id=category_id)
        return points
    except Exception as e:
        logger.error(f"Interest discovery failed: {e}")
        raise HTTPException(status_code=500, detail=f"AI 发现兴趣点失败: {str(e)}")
