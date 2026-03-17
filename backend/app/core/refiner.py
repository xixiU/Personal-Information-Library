"""AI Refiner - AI精炼引擎."""
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from openai import AsyncOpenAI
from sqlalchemy.orm import Session

from app.config import settings
from app.models.result import CrawlResult, RefinedResult
from app.models.task import Task
from app.models.source import Source
from app.models.category import Category

logger = logging.getLogger(__name__)


class RefinerEngine:
    """AI精炼引擎，负责内容精炼."""

    # 精炼提示词模板
    TEMPLATES = {
        "summary": {
            "name": "摘要生成",
            "system": "你是一个专业的内容摘要助手。请为用户提供的文章生成简洁、准确的摘要。",
            "user": "请为以下内容生成摘要（200字以内）：\n\n标题：{title}\n\n内容：\n{content}",
        },
        "keywords": {
            "name": "关键词提取",
            "system": "你是一个专业的关键词提取助手。请从文章中提取最重要的关键词。",
            "user": "请从以下内容中提取5-10个关键词，以JSON数组格式返回：\n\n标题：{title}\n\n内容：\n{content}\n\n返回格式：[\"关键词1\", \"关键词2\", ...]",
        },
        "summary_keywords": {
            "name": "摘要+关键词",
            "system": "你是一个专业的内容分析助手。请为文章生成摘要并提取关键词。",
            "user": """请分析以下内容，生成摘要和关键词：

标题：{title}

内容：
{content}

请以JSON格式返回：
{{
  "summary": "摘要内容（200字以内）",
  "keywords": ["关键词1", "关键词2", ...],
  "category": "文章分类（如：技术、新闻、教程等）",
  "quality_score": 0-100的整数，根据内容质量、信息密度、可读性综合评分
}}""",
        },
    }

    def __init__(self):
        """初始化精炼引擎."""
        self.client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_api_base,
        )
        self.model = settings.openai_model
        self.max_retries = 3

    async def refine(
        self,
        crawl_result: CrawlResult,
        template_name: str = "summary_keywords",
        custom_prompt: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> Optional[RefinedResult]:
        """
        执行精炼任务.

        Args:
            crawl_result: 爬取结果
            template_name: 模板名称
            custom_prompt: 自定义提示词（覆盖模板）
            db: 数据库会话（用于查询分类 prompt）

        Returns:
            精炼结果对象，失败返回None
        """
        try:
            # 检查内容是否为空
            if not crawl_result.content or len(crawl_result.content.strip()) < 50:
                logger.warning(f"Content too short for crawl result {crawl_result.id}")
                return None

            # 尝试从分类获取自定义 prompt
            category_prompt = self._get_category_prompt(crawl_result, db)

            # 构建提示词（优先级：custom_prompt > 分类 prompt > 模板）
            if custom_prompt:
                messages = [
                    {"role": "system", "content": "你是一个专业的内容分析助手。"},
                    {"role": "user", "content": custom_prompt.format(
                        title=crawl_result.title or "无标题",
                        content=self._truncate_content(crawl_result.content),
                    )},
                ]
            elif category_prompt:
                messages = [
                    {"role": "system", "content": category_prompt["system"]},
                    {"role": "user", "content": category_prompt["user"].format(
                        title=crawl_result.title or "无标题",
                        content=self._truncate_content(crawl_result.content),
                    )},
                ]
                template_name = "category_custom"
            else:
                template = self.TEMPLATES.get(template_name)
                if not template:
                    logger.error(f"Template {template_name} not found")
                    return None

                messages = [
                    {"role": "system", "content": template["system"]},
                    {"role": "user", "content": template["user"].format(
                        title=crawl_result.title or "无标题",
                        content=self._truncate_content(crawl_result.content),
                    )},
                ]

            logger.info(f"Refining crawl result {crawl_result.id} with template {template_name}")

            # 调用OpenAI API（带重试）
            response_text = await self._call_openai_with_retry(messages)

            if not response_text:
                logger.error(f"Failed to refine crawl result {crawl_result.id}")
                return None

            # 解析响应
            refined_data = self._parse_response(response_text, template_name)

            # 校验 quality_score
            qs = refined_data.get("quality_score")
            if qs is not None:
                try:
                    qs = int(qs)
                    refined_data["quality_score"] = max(0, min(100, qs))
                except (ValueError, TypeError):
                    refined_data["quality_score"] = None

            # 创建精炼结果
            refined_result = RefinedResult(
                crawl_result_id=crawl_result.id,
                summary=refined_data.get("summary"),
                keywords=refined_data.get("keywords"),
                category=refined_data.get("category"),
                quality_score=refined_data.get("quality_score"),
                meta_data={
                    "template": template_name,
                    "model": self.model,
                    "raw_response": response_text[:500],  # 保存前500字符
                },
                created_at=datetime.utcnow(),
            )

            logger.info(f"Refined result created for crawl result {crawl_result.id}")
            return refined_result

        except Exception as e:
            logger.error(f"Failed to refine crawl result {crawl_result.id}: {e}", exc_info=True)
            return None

    def _get_category_prompt(
        self, crawl_result: CrawlResult, db: Optional[Session]
    ) -> Optional[Dict[str, str]]:
        """从 crawl_result 关联的 source 的分类中获取自定义 prompt."""
        if not db:
            return None

        try:
            # 通过 crawl_result -> task -> source -> category 链路查询
            task = db.query(Task).filter(Task.id == crawl_result.task_id).first()
            if not task or not task.source_id:
                return None

            source = db.query(Source).filter(Source.id == task.source_id).first()
            if not source or not source.category_id:
                return None

            category = db.query(Category).filter(Category.id == source.category_id).first()
            if not category:
                return None

            if category.refine_prompt_system:
                # 构造包含质量评分要求的用户提示词
                quality_instruction = ""
                if category.quality_criteria:
                    quality_instruction = f"\n\n质量评分标准：\n{category.quality_criteria}\n"

                user_prompt = """请分析以下内容：

标题：{{title}}

内容：
{{content}}
{quality_instruction}
请以JSON格式返回：
{{{{
  "summary": "摘要内容（200字以内）",
  "keywords": ["关键词1", "关键词2", ...],
  "category": "文章分类",
  "quality_score": 0-100的整数，根据上述标准评分
}}}}""".format(quality_instruction=quality_instruction)

                logger.info(f"Using category '{category.name}' prompt for crawl result {crawl_result.id}")
                return {
                    "system": category.refine_prompt_system,
                    "user": user_prompt,
                }
        except Exception as e:
            logger.warning(f"Failed to get category prompt: {e}")

        return None

    async def _call_openai_with_retry(self, messages: list) -> Optional[str]:
        """
        调用OpenAI API，带重试机制.

        Args:
            messages: 消息列表

        Returns:
            响应文本，失败返回None
        """
        for attempt in range(self.max_retries):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.3,
                    max_tokens=1000,
                )

                return response.choices[0].message.content

            except Exception as e:
                logger.warning(f"OpenAI API call failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt == self.max_retries - 1:
                    logger.error(f"All retry attempts failed")
                    return None

                # 等待后重试
                import asyncio
                await asyncio.sleep(2 ** attempt)  # 指数退避

        return None

    def _truncate_content(self, content: str, max_length: int = 4000) -> str:
        """
        截断内容到指定长度.

        Args:
            content: 原始内容
            max_length: 最大长度

        Returns:
            截断后的内容
        """
        if len(content) <= max_length:
            return content

        return content[:max_length] + "\n\n...(内容已截断)"

    def _parse_response(self, response_text: str, template_name: str) -> Dict[str, Any]:
        """
        解析AI响应.

        Args:
            response_text: 响应文本
            template_name: 模板名称

        Returns:
            解析后的数据
        """
        result = {}

        try:
            # 尝试解析JSON
            if template_name in ["keywords", "summary_keywords", "category_custom"]:
                import json
                import re

                # 提取JSON部分
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                    result = data
                else:
                    # 尝试提取数组
                    array_match = re.search(r'\[.*\]', response_text, re.DOTALL)
                    if array_match:
                        keywords = json.loads(array_match.group())
                        result["keywords"] = keywords
                    else:
                        # 纯文本响应
                        result["summary"] = response_text.strip()
            else:
                # 纯文本响应
                result["summary"] = response_text.strip()

        except Exception as e:
            logger.warning(f"Failed to parse response as JSON: {e}")
            # 回退到纯文本
            result["summary"] = response_text.strip()

        return result

    @classmethod
    def get_templates(cls) -> Dict[str, Dict[str, str]]:
        """获取所有模板."""
        return cls.TEMPLATES

    @classmethod
    def add_template(cls, name: str, system: str, user: str, description: str = ""):
        """
        添加自定义模板.

        Args:
            name: 模板名称
            system: 系统提示词
            user: 用户提示词模板
            description: 模板描述
        """
        cls.TEMPLATES[name] = {
            "name": description or name,
            "system": system,
            "user": user,
        }
