"""Feedback API - 用户反馈接口."""
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.result import RefinedResult
from app.models.interest import UserFeedback
from app.schemas.interest import UserFeedbackCreate, UserFeedbackResponse, FeedbackAction

logger = logging.getLogger(__name__)

router = APIRouter(tags=["feedback"])

# like 和 dislike 互斥
_EXCLUSIVE_ACTIONS = {
    FeedbackAction.LIKE: FeedbackAction.DISLIKE,
    FeedbackAction.DISLIKE: FeedbackAction.LIKE,
}


@router.post(
    "/api/results/refine/{refined_result_id}/feedback",
    response_model=UserFeedbackResponse,
    status_code=201,
)
async def create_feedback(
    refined_result_id: int,
    feedback: UserFeedbackCreate,
    db: Session = Depends(get_db),
):
    """提交反馈."""
    # 检查 refined_result 是否存在
    result = db.query(RefinedResult).filter(RefinedResult.id == refined_result_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="RefinedResult not found")

    action = feedback.action

    # comment 可多次提交；其他 action 不能重复
    if action != FeedbackAction.COMMENT:
        existing = (
            db.query(UserFeedback)
            .filter(
                UserFeedback.refined_result_id == refined_result_id,
                UserFeedback.action == action.value,
            )
            .first()
        )
        if existing:
            raise HTTPException(status_code=409, detail=f"已存在 {action.value} 反馈")

    # like/dislike 互斥：提交一方时自动移除另一方
    opposite = _EXCLUSIVE_ACTIONS.get(action)
    if opposite:
        db.query(UserFeedback).filter(
            UserFeedback.refined_result_id == refined_result_id,
            UserFeedback.action == opposite.value,
        ).delete()

    db_feedback = UserFeedback(
        refined_result_id=refined_result_id,
        action=action.value,
        comment_text=feedback.comment_text,
    )
    db.add(db_feedback)
    db.commit()
    db.refresh(db_feedback)

    logger.info(f"Created feedback: {db_feedback.id} ({action.value}) for result {refined_result_id}")
    return db_feedback


@router.get(
    "/api/results/refine/{refined_result_id}/feedback",
    response_model=List[UserFeedbackResponse],
)
async def list_feedback(refined_result_id: int, db: Session = Depends(get_db)):
    """获取某条精炼结果的所有反馈."""
    feedbacks = (
        db.query(UserFeedback)
        .filter(UserFeedback.refined_result_id == refined_result_id)
        .order_by(UserFeedback.created_at.desc())
        .all()
    )
    return feedbacks


@router.delete("/api/feedback/{feedback_id}", status_code=204)
async def delete_feedback(feedback_id: int, db: Session = Depends(get_db)):
    """删除反馈（撤销）."""
    feedback = db.query(UserFeedback).filter(UserFeedback.id == feedback_id).first()
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")

    db.delete(feedback)
    db.commit()

    logger.info(f"Deleted feedback: {feedback_id}")
    return None


@router.get("/api/feedback/stats")
async def feedback_stats(db: Session = Depends(get_db)):
    """反馈统计（各 action 数量）."""
    rows = (
        db.query(UserFeedback.action, func.count(UserFeedback.id))
        .group_by(UserFeedback.action)
        .all()
    )
    stats = {action: count for action, count in rows}
    total = sum(stats.values())
    return {"total": total, "by_action": stats}
