"""Notification Channels API - 通知渠道管理."""
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.notification import NotificationChannel, NotificationRule
from app.schemas.notification import (
    NotificationChannelCreate,
    NotificationChannelUpdate,
    NotificationChannelResponse,
)
from app.core.notifiers.webhook import WebhookNotifier
from app.core.notifiers.telegram import TelegramNotifier
from app.core.notifiers.feishu import FeishuNotifier

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/notification-channels", tags=["notification-channels"])

_NOTIFIER_MAP = {
    "webhook": WebhookNotifier,
    "telegram": TelegramNotifier,
    "feishu": FeishuNotifier,
}


@router.post("", response_model=NotificationChannelResponse, status_code=201)
async def create_channel(data: NotificationChannelCreate, db: Session = Depends(get_db)):
    """创建通知渠道."""
    # 验证配置
    notifier_cls = _NOTIFIER_MAP.get(data.channel_type)
    if notifier_cls:
        ok, err = notifier_cls(data.config).validate_config()
        if not ok:
            raise HTTPException(status_code=400, detail=f"配置验证失败: {err}")

    channel = NotificationChannel(
        name=data.name,
        channel_type=data.channel_type,
        config=data.config,
        enabled=data.enabled,
    )
    db.add(channel)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=400, detail="渠道名称已存在")
    db.refresh(channel)
    logger.info(f"Created notification channel: {channel.id}")
    return channel


@router.get("", response_model=List[NotificationChannelResponse])
async def list_channels(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """获取通知渠道列表."""
    return db.query(NotificationChannel).offset(skip).limit(limit).all()


@router.get("/{channel_id}", response_model=NotificationChannelResponse)
async def get_channel(channel_id: int, db: Session = Depends(get_db)):
    """获取通知渠道详情."""
    channel = db.query(NotificationChannel).filter(NotificationChannel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="渠道不存在")
    return channel


@router.put("/{channel_id}", response_model=NotificationChannelResponse)
async def update_channel(channel_id: int, data: NotificationChannelUpdate, db: Session = Depends(get_db)):
    """更新通知渠道."""
    channel = db.query(NotificationChannel).filter(NotificationChannel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="渠道不存在")

    update_data = data.model_dump(exclude_unset=True)

    # 如果更新了 config，验证配置
    if "config" in update_data:
        ch_type = update_data.get("channel_type", channel.channel_type)
        notifier_cls = _NOTIFIER_MAP.get(ch_type)
        if notifier_cls:
            ok, err = notifier_cls(update_data["config"]).validate_config()
            if not ok:
                raise HTTPException(status_code=400, detail=f"配置验证失败: {err}")

    for key, value in update_data.items():
        setattr(channel, key, value)

    db.commit()
    db.refresh(channel)
    return channel


@router.delete("/{channel_id}", status_code=204)
async def delete_channel(channel_id: int, db: Session = Depends(get_db)):
    """删除通知渠道."""
    channel = db.query(NotificationChannel).filter(NotificationChannel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="渠道不存在")

    # 检查关联规则
    rule_count = db.query(NotificationRule).filter(NotificationRule.channel_id == channel_id).count()
    if rule_count > 0:
        raise HTTPException(status_code=400, detail=f"该渠道下有 {rule_count} 条通知规则，请先删除规则")

    db.delete(channel)
    db.commit()


@router.post("/{channel_id}/test")
async def test_channel(channel_id: int, db: Session = Depends(get_db)):
    """测试通知渠道."""
    channel = db.query(NotificationChannel).filter(NotificationChannel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="渠道不存在")

    notifier_cls = _NOTIFIER_MAP.get(channel.channel_type)
    if not notifier_cls:
        raise HTTPException(status_code=400, detail=f"不支持的渠道类型: {channel.channel_type}")

    notifier = notifier_cls(channel.config)
    success, error = await notifier.send_test()

    return {
        "success": success,
        "message": "测试消息发送成功" if success else f"测试消息发送失败: {error}" if error else "测试消息发送失败，请检查配置",
    }
