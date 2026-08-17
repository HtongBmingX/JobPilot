"""简历库 Pydantic schemas"""

from pydantic import BaseModel, Field
from datetime import datetime


class ResumeCreateRequest(BaseModel):
    """创建简历"""
    name: str = Field(..., min_length=1, max_length=100)
    content: str = ""
    is_default: bool = False


class ResumeUpdateRequest(BaseModel):
    """更新简历（所有字段可选）"""
    name: str | None = None
    content: str | None = None
    is_default: bool | None = None


class ResumeResponse(BaseModel):
    """简历响应"""
    id: int
    user_id: int
    name: str
    content: str
    is_default: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
