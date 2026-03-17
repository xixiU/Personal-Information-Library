"""WebhookNotifier - 通用 HTTP Webhook 通知."""
import asyncio
import hashlib
import hmac
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


class WebhookNotifier(BaseNotifier):
    """通用 Webhook 通知发送器."""

    MAX_RETRIES = 3
    TIMEOUT = 10

    async def send(self, message: NotificationMessage) -> bool:
        body = self._render_body(message)
        success, _ = await self._do_send(body)
        return success

    async def send_batch(self, message: BatchNotificationMessage) -> bool:
        body = self._render_batch_body(message)
        success, _ = await self._do_send(body)
        return success

    def validate_config(self) -> Tuple[bool, str]:
        url = self.config.get("url")
        if not url:
            return False, "缺少 url 配置"
        if not url.startswith(("http://", "https://")):
            return False, "url 必须以 http:// 或 https:// 开头"
        method = self.config.get("method", "POST").upper()
        if method not in ("POST", "PUT"):
            return False, "method 仅支持 POST 或 PUT"
        return True, ""

    async def send_test(self) -> Tuple[bool, str]:
        """发送测试消息，返回 (成功, 错误信息)."""
        test_msg = NotificationMessage(
            title="测试通知",
            summary="这是一条测试消息，用于验证 Webhook 配置是否正确。",
            url="https://example.com/test",
            quality_score=88,
            keywords=["测试"],
            category_name="测试分类",
            source_name="测试信源",
            timestamp="2026-01-01T00:00:00",
        )
        body = self._render_body(test_msg)
        return await self._do_send(body)

    async def _do_send(self, body: str) -> tuple[bool, str]:
        """发送请求，返回 (成功, 错误信息)."""
        url = self.config["url"]
        method = self.config.get("method", "POST").upper()
        headers = dict(self.config.get("headers") or {})
        headers.setdefault("Content-Type", "application/json")

        secret = self.config.get("secret")
        if secret:
            signature = hmac.new(
                secret.encode(), body.encode(), hashlib.sha256
            ).hexdigest()
            headers["X-Signature-256"] = f"sha256={signature}"

        last_error = ""
        async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
            for attempt in range(self.MAX_RETRIES):
                try:
                    resp = await client.request(
                        method, url, content=body, headers=headers
                    )
                    resp.raise_for_status()

                    # 检查响应体中的业务错误码（飞书等平台）
                    try:
                        resp_data = resp.json()
                        code = resp_data.get("code")
                        if code is not None and code != 0:
                            msg = resp_data.get("msg", "unknown")
                            last_error = f"code={code}, msg={msg}"
                            logger.error(f"Webhook business error: {last_error}, url={url}")
                            if attempt < self.MAX_RETRIES - 1:
                                await asyncio.sleep(2 ** attempt)
                            continue
                    except (ValueError, AttributeError):
                        pass  # 非 JSON 响应，跳过业务码检查

                    logger.info(f"Webhook sent to {url}, status={resp.status_code}")
                    return True, ""
                except Exception as e:
                    last_error = str(e)
                    logger.warning(
                        f"Webhook attempt {attempt + 1}/{self.MAX_RETRIES} failed: {e}"
                    )
                    if attempt < self.MAX_RETRIES - 1:
                        await asyncio.sleep(2 ** attempt)

        logger.error(f"Webhook send failed after {self.MAX_RETRIES} retries: {url}")
        return False, last_error

    def _render_body(self, message: NotificationMessage) -> str:
        template = self.config.get("body_template")
        if template:
            return self._render_template(template, {
                "title": message.title,
                "summary": message.summary,
                "url": message.url,
                "quality_score": str(message.quality_score or "N/A"),
                "keywords": ", ".join(message.keywords),
                "category_name": message.category_name,
                "source_name": message.source_name,
                "timestamp": message.timestamp,
            })

        return json.dumps({
            "title": message.title,
            "summary": message.summary,
            "url": message.url,
            "quality_score": message.quality_score,
            "keywords": message.keywords,
            "category_name": message.category_name,
            "source_name": message.source_name,
            "timestamp": message.timestamp,
        }, ensure_ascii=False)

    def _render_batch_body(self, message: BatchNotificationMessage) -> str:
        items = [
            {
                "title": item.title,
                "summary": item.summary,
                "url": item.url,
                "quality_score": item.quality_score,
            }
            for item in message.items
        ]
        return json.dumps({
            "category_name": message.category_name,
            "total_count": message.total_count,
            "items": items,
        }, ensure_ascii=False)

    @staticmethod
    def _render_template(template: str, variables: dict) -> str:
        result = template
        for key, value in variables.items():
            result = result.replace("{{" + key + "}}", str(value))
        return result
