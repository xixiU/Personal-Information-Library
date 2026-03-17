"""TelegramNotifier - Telegram Bot 通知."""
import asyncio
import logging
from typing import Tuple

import httpx

from app.core.notifiers.base import (
    BaseNotifier,
    NotificationMessage,
    BatchNotificationMessage,
)

logger = logging.getLogger(__name__)

# Markdown V1 特殊字符（仅需转义少数字符）
_MD_ESCAPE_CHARS = ("_", "*", "[", "]", "(", ")", "`")


def _escape_md(text: str) -> str:
    """转义 Markdown V1 特殊字符."""
    for ch in _MD_ESCAPE_CHARS:
        text = text.replace(ch, f"\\{ch}")
    return text


class TelegramNotifier(BaseNotifier):
    """Telegram Bot 通知发送器."""

    API_BASE = "https://api.telegram.org/bot{token}"
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
        if not self.config.get("bot_token"):
            return False, "缺少 bot_token 配置"
        if not self.config.get("chat_id"):
            return False, "缺少 chat_id 配置"
        return True, ""

    async def send_test(self) -> Tuple[bool, str]:
        """发送测试消息，返回 (成功, 错误信息)."""
        test_msg = NotificationMessage(
            title="测试通知",
            summary="这是一条测试消息，用于验证 Telegram Bot 配置是否正确。",
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
        """发送消息，返回 (成功, 错误信息)."""
        token = self.config["bot_token"]
        url = f"{self.API_BASE.format(token=token)}/sendMessage"
        payload = {
            "chat_id": self.config["chat_id"],
            "text": text,
            "parse_mode": self.config.get("parse_mode", "Markdown"),
            "disable_web_page_preview": self.config.get("disable_preview", False),
        }
        if self.config.get("disable_notification"):
            payload["disable_notification"] = True

        last_error = ""
        async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
            for attempt in range(self.MAX_RETRIES):
                try:
                    resp = await client.post(url, json=payload)
                    if resp.status_code == 200:
                        resp_data = resp.json()
                        if resp_data.get("ok"):
                            logger.info(f"Telegram message sent to {self.config['chat_id']}")
                            return True, ""
                        last_error = resp_data.get("description", "unknown error")
                        logger.warning(f"Telegram API error: {last_error}")
                    else:
                        last_error = f"HTTP {resp.status_code}: {resp.text}"
                        logger.warning(f"Telegram API returned {resp.status_code}: {resp.text}")
                except Exception as e:
                    last_error = str(e)
                    logger.warning(
                        f"Telegram attempt {attempt + 1}/{self.MAX_RETRIES} failed: {e}"
                    )
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(2 ** attempt)

        logger.error(f"Telegram send failed after {self.MAX_RETRIES} retries")
        return False, last_error

    def _format_message(self, message: NotificationMessage) -> str:
        score = f" | 质量: {message.quality_score}/100" if message.quality_score else ""
        keywords = ", ".join(message.keywords) if message.keywords else ""
        kw_line = f"\n🏷 {keywords}" if keywords else ""

        return (
            f"📢 *{_escape_md(message.title)}*\n\n"
            f"{_escape_md(message.summary)}\n"
            f"{kw_line}\n"
            f"📂 {_escape_md(message.category_name)} | 📡 {_escape_md(message.source_name)}{score}\n"
            f"🔗 {message.url}"
        )

    def _format_batch_message(self, message: BatchNotificationMessage) -> str:
        header = f"📋 *{_escape_md(message.category_name)}* — {message.total_count} 条新内容\n\n"
        items = []
        for i, item in enumerate(message.items[:10], 1):
            score = f" ({item.quality_score}分)" if item.quality_score else ""
            items.append(f"{i}\\. [{_escape_md(item.title)}]({item.url}){score}")

        if message.total_count > 10:
            items.append(f"\n\\.\\.\\.还有 {message.total_count - 10} 条")

        return header + "\n".join(items)
