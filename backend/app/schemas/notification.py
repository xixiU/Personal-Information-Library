"""Notification schemas - 通知相关的 Pydantic 模型."""
from typing import Optional, Any
from datetime import datetime

from pydantic import BaseModel, Field


# --- NotificationChannel ---

class NotificationChannelCreate(BaseModel):
    """创建通知渠道."""

    name: str = Field(..., min_length=1, max_length=100)
    channel_type: str = Field(..., pattern="^(webhook|telegram|feishu)$")
    config: dict = Field(default_factory=dict)
    enabled: bool = True


class NotificationChannelUpdate(BaseModel):
    """更新通知渠道."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    channel_type: Optional[str] = Field(None, pattern="^(webhook|telegram|feishu)$")
    config: Optional[dict] = None
    enabled: Optional[bool] = None


class NotificationChannelResponse(BaseModel):
    """通知渠道响应."""

    id: int
    name: str
    channel_type: str
    config: dict
    enabled: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

    def model_post_init(self, __context: Any) -> None:
        """敏感字段脱敏."""
        if self.config:
            masked = dict(self.config)
            for key in ("bot_token", "secret"):
                if key in masked and masked[key]:
                    masked[key] = "***"
            self.config = masked


# --- NotificationRule ---

class NotificationRuleCreate(BaseModel):
    """创建通知规则."""

    name: str = Field(..., min_length=1, max_length=100)
    channel_id: int
    rule_type: str = Field(..., pattern="^(new_content|quality_threshold|keyword_match)$")
    notify_mode: str = Field(default="instant", pattern="^(instant|batch)$")
    conditions: dict = Field(default_factory=dict)
    message_template: Optional[str] = None
    enabled: bool = True


class NotificationRuleUpdate(BaseModel):
    """更新通知规则."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    channel_id: Optional[int] = None
    rule_type: Optional[str] = Field(None, pattern="^(new_content|quality_threshold|keyword_match)$")
    notify_mode: Optional[str] = Field(None, pattern="^(instant|batch)$")
    conditions: Optional[dict] = None
    message_template: Optional[str] = None
    enabled: Optional[bool] = None


class NotificationRuleResponse(BaseModel):
    """通知规则响应."""

    id: int
    name: str
    category_id: int
    channel_id: int
    rule_type: str
    notify_mode: str
    conditions: dict
    message_template: Optional[str] = None
    enabled: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- NotificationLog ---

class NotificationLogResponse(BaseModel):
    """通知日志响应."""

    id: int
    rule_id: int
    channel_id: int
    refined_result_id: Optional[int] = None
    batch_id: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    sent_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True
