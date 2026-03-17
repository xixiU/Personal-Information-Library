"""Notification models - 通知渠道、规则和日志."""
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON,
)
from sqlalchemy.orm import relationship

from app.database import Base


class NotificationChannel(Base):
    """通知渠道."""

    __tablename__ = "notification_channels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    channel_type = Column(String(20), nullable=False)  # webhook / telegram
    config = Column(JSON, nullable=False, default=dict)
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    rules = relationship("NotificationRule", back_populates="channel")


class NotificationRule(Base):
    """通知规则."""

    __tablename__ = "notification_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False, index=True)
    channel_id = Column(Integer, ForeignKey("notification_channels.id"), nullable=False, index=True)
    rule_type = Column(String(30), nullable=False)  # new_content / quality_threshold / keyword_match
    notify_mode = Column(String(20), nullable=False, default="instant")  # instant / batch
    conditions = Column(JSON, nullable=False, default=dict)
    message_template = Column(Text, nullable=True)
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    category = relationship("Category", lazy="joined")
    channel = relationship("NotificationChannel", back_populates="rules", lazy="joined")
    logs = relationship("NotificationLog", back_populates="rule")


class NotificationLog(Base):
    """通知发送日志."""

    __tablename__ = "notification_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rule_id = Column(Integer, ForeignKey("notification_rules.id"), nullable=False, index=True)
    channel_id = Column(Integer, ForeignKey("notification_channels.id"), nullable=False, index=True)
    refined_result_id = Column(Integer, ForeignKey("refined_results.id"), nullable=True, index=True)
    batch_id = Column(String(36), nullable=True, index=True)  # 聚合批次 UUID
    status = Column(String(20), nullable=False, default="pending")  # pending / success / failed
    error_message = Column(Text, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    rule = relationship("NotificationRule", back_populates="logs")
