"""Highlights API - 高亮笔记管理（任务 D）."""
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.highlight import Highlight
from app.models.result import CrawlResult, RefinedResult
from app.schemas.highlight import HighlightCreate, HighlightUpdate, HighlightResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/highlights", tags=["highlights"])


@router.post("", response_model=HighlightResponse, status_code=201)
async def create_highlight(data: HighlightCreate, db: Session = Depends(get_db)):
    """创建高亮."""
    # 验证精炼结果存在
    refined = db.query(RefinedResult).filter(RefinedResult.id == data.refined_result_id).first()
    if not refined:
        raise HTTPException(status_code=404, detail="精炼结果不存在")

    highlight = Highlight(
        refined_result_id=data.refined_result_id,
        highlight_text=data.highlight_text,
        note=data.note,
        position_start=data.position_start,
        position_end=data.position_end,
        color=data.color,
    )
    db.add(highlight)
    db.commit()
    db.refresh(highlight)
    logger.info(f"Created highlight {highlight.id} for refined_result {data.refined_result_id}")
    return highlight


@router.put("/{highlight_id}", response_model=HighlightResponse)
async def update_highlight(
    highlight_id: int, data: HighlightUpdate, db: Session = Depends(get_db)
):
    """更新高亮（主要改批注/颜色）."""
    highlight = db.query(Highlight).filter(Highlight.id == highlight_id).first()
    if not highlight:
        raise HTTPException(status_code=404, detail="高亮不存在")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(highlight, key, value)

    db.commit()
    db.refresh(highlight)
    return highlight


@router.delete("/{highlight_id}", status_code=204)
async def delete_highlight(highlight_id: int, db: Session = Depends(get_db)):
    """删除高亮."""
    highlight = db.query(Highlight).filter(Highlight.id == highlight_id).first()
    if not highlight:
        raise HTTPException(status_code=404, detail="高亮不存在")

    db.delete(highlight)
    db.commit()


@router.get("/export", response_class=PlainTextResponse)
async def export_highlights(
    format: str = Query("markdown", pattern="^(markdown)$"),
    db: Session = Depends(get_db),
):
    """导出所有高亮为 Markdown（按 refined_result_id 分组、按 created_at 排序）."""
    # 查询所有高亮，按 result 分组、按创建时间排序
    highlights = (
        db.query(Highlight)
        .order_by(Highlight.refined_result_id, Highlight.created_at.asc())
        .all()
    )

    if not highlights:
        return PlainTextResponse(
            content="# 我的高亮笔记\n\n暂无高亮。\n",
            media_type="text/markdown; charset=utf-8",
        )

    # 按 refined_result_id 分组
    grouped: dict[int, list[Highlight]] = {}
    for h in highlights:
        grouped.setdefault(h.refined_result_id, []).append(h)

    lines = ["# 我的高亮笔记", ""]

    for refined_result_id, items in grouped.items():
        # 获取文章标题和 URL
        title = "未知文章"
        url = ""
        refined = db.query(RefinedResult).filter(RefinedResult.id == refined_result_id).first()
        if refined:
            crawl = db.query(CrawlResult).filter(
                CrawlResult.id == refined.crawl_result_id
            ).first()
            if crawl:
                title = crawl.title or "未知文章"
                url = crawl.url or ""

        if url:
            lines.append(f"## [{title}]({url})")
        else:
            lines.append(f"## {title}")
        lines.append("")

        for h in items:
            lines.append(f"> {h.highlight_text}")
            if h.note:
                lines.append(f"**批注**：{h.note}")
            lines.append("")

    content = "\n".join(lines)
    return PlainTextResponse(content=content, media_type="text/markdown; charset=utf-8")


def list_highlights_by_result(result_id: int, db: Session) -> List[Highlight]:
    """列出某个精炼结果的所有高亮（供 results 路由复用）."""
    return (
        db.query(Highlight)
        .filter(Highlight.refined_result_id == result_id)
        .order_by(Highlight.created_at.asc())
        .all()
    )
