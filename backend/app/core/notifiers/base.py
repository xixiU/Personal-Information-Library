"""BaseNotifier - 通知发送器抽象基类."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Tuple, List


@dataclass
class NotificationMessage:
    """单条通知消息."""

    title: str
    summary: str
    url: str
    quality_score: Optional[int]
    keywords: List[str]
    category_name: str
    source_name: str
    timestamp: str


@dataclass
class BatchNotificationMessage:
    """聚合通知消息."""

    category_name: str
    items: List[NotificationMessage] = field(default_factory=list)
    total_count: int = 0


class BaseNotifier(ABC):
    """通知发送器抽象基类."""

    def __init__(self, config: dict):
        self.config = config

    @abstractmethod
    async def send(self, message: NotificationMessage) -> bool:
        """发送单条通知."""

    @abstractmethod
    async def send_batch(self, message: BatchNotificationMessage) -> bool:
        """发送聚合通知."""

    @abstractmethod
    def validate_config(self) -> Tuple[bool, str]:
        """验证配置，返回 (是否合法, 错误信息)."""

    @abstractmethod
    async def send_test(self) -> Tuple[bool, str]:
        """发送测试消息，返回 (成功, 错误信息)."""
