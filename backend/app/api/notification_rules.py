"""Notification Rules API - 通知规则管理."""
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.category import Category
from app.models.notification import NotificationChannel, NotificationRule
from app.schemas.notification import (
    NotificationRuleCreate,
    NotificationRuleUpdate,
    NotificationRuleResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/categories/{category_id}/notification-rules", tags=["notification-rules"])


@router.post("", response_model=NotificationRuleResponse, status_code=201)
async def create_rule(
    category_id: int, data: NotificationRuleCreate, db: Session = Depends(get_db)
):
    """创建通知规则."""
    # 验证 category 存在
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="分类不存在")

    # 验证 channel 存在
    channel = db.query(NotificationChannel).filter(NotificationChannel.id == data.channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="通知渠道不存在")

    rule = NotificationRule(
        name=data.name,
        category_id=category_id,
        channel_id=data.channel_id,
        rule_type=data.rule_type,
        notify_mode=data.notify_mode,
        conditions=data.conditions,
        message_template=data.message_template,
        enabled=data.enabled,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    logger.info(f"Created notification rule: {rule.id} for category {category_id}")
    return rule


@router.get("", response_model=List[NotificationRuleResponse])
async def list_rules(category_id: int, db: Session = Depends(get_db)):
    """获取分类下的通知规则列表."""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="分类不存在")

    return (
        db.query(NotificationRule)
        .filter(NotificationRule.category_id == category_id)
        .all()
    )


@router.put("/{rule_id}", response_model=NotificationRuleResponse)
async def update_rule(
    category_id: int, rule_id: int, data: NotificationRuleUpdate, db: Session = Depends(get_db)
):
    """更新通知规则."""
    rule = (
        db.query(NotificationRule)
        .filter(NotificationRule.id == rule_id, NotificationRule.category_id == category_id)
        .first()
    )
    if not rule:
        raise HTTPException(status_code=404, detail="通知规则不存在")

    update_data = data.model_dump(exclude_unset=True)

    # 如果更新了 channel_id，验证存在性
    if "channel_id" in update_data:
        channel = db.query(NotificationChannel).filter(
            NotificationChannel.id == update_data["channel_id"]
        ).first()
        if not channel:
            raise HTTPException(status_code=404, detail="通知渠道不存在")

    for key, value in update_data.items():
        setattr(rule, key, value)

    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/{rule_id}", status_code=204)
async def delete_rule(category_id: int, rule_id: int, db: Session = Depends(get_db)):
    """删除通知规则."""
    rule = (
        db.query(NotificationRule)
        .filter(NotificationRule.id == rule_id, NotificationRule.category_id == category_id)
        .first()
    )
    if not rule:
        raise HTTPException(status_code=404, detail="通知规则不存在")

    db.delete(rule)
    db.commit()
