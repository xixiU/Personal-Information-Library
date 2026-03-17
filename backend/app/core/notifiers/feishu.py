"""FeishuNotifier - 飞书 Webhook 通知."""
import asyncio
import json
import logging
from typing import Tuple

import httpx

from app.core.notifiers.base import (
    BaseNotifier,
    NotificationMessage,
    BatchNotificationMessage,
)

logger = logging.getLogger(__name__)


class FeishuNotifier(BaseNotifier):
    """飞书 Webhook 通知发送器."""

    MAX_RETRIES = 3
    TIMEOUT = 10

    async def send(self, message: NotificationMessage) -> bool:
        text = self._format_message(message)
        success, _ = await self._send_message(text)
        return success

    async def send_batch(self, message: BatchNotificationMessage) -> bool:
        text = self._format_batch_message(message)
        success, _ = await self._send_message(text)
        return success

    def validate_config(self) -> Tuple[bool, str]:
        url = self.config.get("webhook_url")
        if not url:
            return False, "缺少 webhook_url 配置"
        if not url.startswith("https://"):
            return False, "webhook_url 必须以 https:// 开头"
        return True, ""

    async def send_test(self) -> Tuple[bool, str]:
        """发送测试消息，返回 (成功, 错误信息)."""
        test_msg = NotificationMessage(
            title="测试通知",
            summary="这是一条测试消息，用于验证飞书 Webhook 配置是否正确。",
            url="https://example.com/test",
            quality_score=88,
            keywords=["测试"],
            category_name="测试分类",
            source_name="测试信源",
            timestamp="2026-01-01T00:00:00",
        )
        text = self._format_message(test_msg)
        return await self._send_message(text)

    async def _send_message(self, text: str) -> Tuple[bool, str]:
        """发送消息到飞书，返回 (成功, 错误信息)."""
        url = self.config["webhook_url"]

        # 默认使用消息卡片格式（interactive）
        use_card = self.config.get("use_card", True)

        if use_card:
            payload = self._build_card_payload(text)
        else:
            # 纯文本格式（兼容旧配置）
            payload = {"msg_type": "text", "content": {"text": text}}

        last_error = ""
        async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
            for attempt in range(self.MAX_RETRIES):
                try:
                    resp = await client.post(url, json=payload)
                    data = resp.json()
                    code = data.get("code", data.get("StatusCode"))
                    if code == 0:
                        logger.info(f"Feishu message sent via {url[:50]}...")
                        return True, ""
                    msg = data.get("msg", data.get("StatusMessage", "unknown"))
                    last_error = f"code={code}, msg={msg}"
                    logger.warning(f"Feishu API error: {last_error}")
                except Exception as e:
                    last_error = str(e)
                    logger.warning(
                        f"Feishu attempt {attempt + 1}/{self.MAX_RETRIES} failed: {e}"
                    )
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(2 ** attempt)

        logger.error(f"Feishu send failed after {self.MAX_RETRIES} retries")
        return False, last_error

    def _build_card_payload(self, text: str) -> dict:
        """构建飞书消息卡片 payload."""
        # 从文本中提取标题（第一行）和内容
        lines = text.split("\n", 1)
        title = lines[0].replace("📢 ", "").strip()
        content = lines[1].strip() if len(lines) > 1 else text

        return {
            "msg_type": "interactive",
            "card": {
                "config": {
                    "wide_screen_mode": True,
                },
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": title,
                    },
                    "template": "blue",
                },
                "elements": [
                    {
                        "tag": "markdown",
                        "content": content,
                    }
                ],
            },
        }

    def _format_message(self, message: NotificationMessage) -> str:
        """格式化单条消息为飞书卡片格式."""
        # 标题行（用于卡片 header）
        title = message.title

        # 内容行（用于卡片 body markdown）
        lines = []
        lines.append(f"**摘要**: {message.summary}")

        if message.keywords:
            keywords = ", ".join(message.keywords)
            lines.append(f"**关键词**: {keywords}")

        lines.append(f"**分类**: {message.category_name}")
        lines.append(f"**来源**: {message.source_name}")

        if message.quality_score is not None:
            lines.append(f"**质量评分**: {message.quality_score}/100")

        lines.append(f"\n[查看原文]({message.url})")

        return f"{title}\n" + "\n".join(lines)

    def _format_batch_message(self, message: BatchNotificationMessage) -> str:
        """格式化批量消息为飞书卡片格式."""
        # 标题行（用于卡片 header）
        title = f"{message.category_name} — {message.total_count} 条新内容"

        # 内容行（用于卡片 body markdown）
        lines = []
        for i, item in enumerate(message.items[:10], 1):
            score = f" **({item.quality_score}分)**" if item.quality_score else ""
            lines.append(f"{i}. **{item.title}**{score}")
            lines.append(f"   [查看原文]({item.url})")
            if i < min(len(message.items), 10):
                lines.append("")  # 空行分隔

        if message.total_count > 10:
            lines.append(f"\\n---\\n**...还有 {message.total_count - 10} 条**")

        return f"{title}\n" + "\n".join(lines)
