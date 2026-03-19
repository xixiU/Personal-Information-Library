"""Interest schemas - 用户反馈和兴趣点的Pydantic模型."""
from enum import Enum
from typing import Optional, List
from datetime import datetime

from pydantic import BaseModel, Field, model_validator


# ---- UserFeedback ----

class FeedbackAction(str, Enum):
    """反馈动作类型."""
    LIKE = "like"
    COLLECT = "collect"
    DISLIKE = "dislike"
    COMMENT = "comment"


class UserFeedbackCreate(BaseModel):
    """创建用户反馈请求."""
    action: FeedbackAction
    comment_text: Optional[str] = None

    @model_validator(mode="after")
    def validate_comment(self):
        if self.action == FeedbackAction.COMMENT and not self.comment_text:
            raise ValueError("action 为 comment 时 comment_text 不能为空")
        return self


class UserFeedbackResponse(BaseModel):
    """用户反馈响应."""
    id: int
    refined_result_id: int
    action: str
    comment_text: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ---- InterestPoint ----

class CategoryBrief(BaseModel):
    """分类简要信息."""
    id: int
    name: str
    color: str = "#1677ff"

    class Config:
        from_attributes = True


class InterestPointCreate(BaseModel):
    """创建兴趣点请求."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    weight: float = Field(default=0.5, ge=0.0, le=1.0)
    category_id: Optional[int] = None
    keywords: List[str] = Field(..., min_length=1)


class InterestPointUpdate(BaseModel):
    """更新兴趣点请求."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    weight: Optional[float] = Field(None, ge=0.0, le=1.0)
    category_id: Optional[int] = None
    keywords: Optional[List[str]] = Field(None, min_length=1)
    is_active: Optional[bool] = None


class InterestPointResponse(BaseModel):
    """兴趣点响应."""
    id: int
    name: str
    description: Optional[str] = None
    source: str
    weight: float
    category_id: Optional[int] = None
    keywords: list
    is_active: bool
    created_at: datetime
    updated_at: datetime
    category: Optional[CategoryBrief] = None

    class Config:
        from_attributes = True
