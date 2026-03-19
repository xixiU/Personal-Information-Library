"""InterestDiscoverer - AI 发现兴趣点服务."""
import json
import logging
from collections import defaultdict
from typing import List, Optional

from openai import AsyncOpenAI
from sqlalchemy.orm import Session

from app.config import settings
from app.models.result import RefinedResult
from app.models.interest import UserFeedback, InterestPoint

logger = logging.getLogger(__name__)

DISCOVER_SYSTEM_PROMPT = """你是一个用户兴趣分析助手。根据用户阅读内容的关键词频率和反馈行为，发现潜在的兴趣点。

你需要：
1. 分析高频关键词和用户正向反馈（like/collect）关联的关键词
2. 结合已有兴趣点，避免重复
3. 发现新的、有意义的兴趣主题

返回 JSON 数组，每个元素格式：
{
  "name": "兴趣点名称（简短）",
  "description": "描述这个兴趣点代表什么",
  "keywords": ["关联关键词1", "关联关键词2", ...],
  "weight": 0.5  // 建议权重 0.0~1.0，基于出现频率和正向反馈强度
}

只返回 JSON 数组，不要其他内容。如果没有发现有价值的兴趣点，返回空数组 []。"""


class InterestDiscoverer:
    """AI 兴趣点发现引擎."""

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_api_base,
        )
        self.model = settings.openai_model

    async def discover(
        self,
        db: Session,
        days: int = 30,
        category_id: Optional[int] = None,
    ) -> List[dict]:
        """发现兴趣点候选."""
        # 1. 收集近 N 天的 RefinedResult
        from datetime import datetime, timedelta

        since = datetime.utcnow() - timedelta(days=days)
        query = db.query(RefinedResult).filter(RefinedResult.created_at >= since)
        if category_id:
            query = query.filter(RefinedResult.category == str(category_id))
        results = query.all()

        if not results:
            logger.info("No refined results found for interest discovery")
            return []

        # 2. 构建加权关键词频率表
        freq = defaultdict(float)
        result_ids = [r.id for r in results]

        # 获取反馈数据
        feedbacks = (
            db.query(UserFeedback)
            .filter(UserFeedback.refined_result_id.in_(result_ids))
            .all()
        )
        feedback_map = defaultdict(list)
        for fb in feedbacks:
            feedback_map[fb.refined_result_id].append(fb.action)

        for result in results:
            if not result.keywords:
                continue
            for kw in result.keywords:
                freq[kw] += 1.0
                actions = feedback_map.get(result.id, [])
                if "like" in actions or "collect" in actions:
                    freq[kw] += 2.0  # 正向反馈加权
                if "dislike" in actions:
                    freq[kw] -= 1.0  # 负向反馈扣减

        if not freq:
            logger.info("No keywords found for interest discovery")
            return []

        # 3. 获取已有兴趣点
        existing_points = db.query(InterestPoint).all()
        existing_names = {p.name.lower() for p in existing_points}
        existing_keywords = []
        for p in existing_points:
            existing_keywords.extend(p.keywords or [])

        # 4. 构建 prompt
        sorted_keywords = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:50]
        keywords_text = ", ".join(f"{kw}({score:.1f})" for kw, score in sorted_keywords)

        # 收集用户批注
        comments = (
            db.query(UserFeedback)
            .filter(
                UserFeedback.refined_result_id.in_(result_ids),
                UserFeedback.action == "comment",
            )
            .all()
        )
        comments_text = "\n".join(
            f"- {c.comment_text}" for c in comments if c.comment_text
        )

        user_prompt = f"""加权关键词频率（关键词(分数)）：
{keywords_text}

已有兴趣点：{', '.join(existing_names) if existing_names else '无'}

用户批注：
{comments_text if comments_text else '无'}

请分析并发现 3-5 个新的兴趣点候选。不要重复已有兴趣点。"""

        # 5. 调用 AI
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": DISCOVER_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.5,
                max_tokens=1500,
            )
            content = response.choices[0].message.content.strip()

            # 解析 JSON（处理可能的 markdown 包裹）
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()

            candidates = json.loads(content)
        except Exception as e:
            logger.error(f"AI interest discovery failed: {e}")
            raise

        # 6. 写入数据库（去重，source=ai_discovered, is_active=false）
        created = []
        for item in candidates:
            name = item.get("name", "").strip()
            if not name or name.lower() in existing_names:
                continue

            point = InterestPoint(
                name=name,
                description=item.get("description", ""),
                source="ai_discovered",
                weight=max(0.0, min(1.0, float(item.get("weight", 0.5)))),
                keywords=item.get("keywords", []),
                is_active=False,
            )
            db.add(point)
            existing_names.add(name.lower())
            created.append(point)

        if created:
            db.commit()
            for p in created:
                db.refresh(p)

        logger.info(f"AI discovered {len(created)} new interest points")
        return created
