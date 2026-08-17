"""投递记录 Pydantic schemas"""

from pydantic import BaseModel, Field
from datetime import datetime


class ApplicationCreateRequest(BaseModel):
    """创建投递记录"""
    company: str = Field(..., min_length=1, max_length=100)
    position: str = Field(..., min_length=1, max_length=100)
    jd_text: str | None = None
    match_score: str | None = None
    match_summary: str | None = None
    applied_at: str | None = None
    notes: str | None = None


class ApplicationUpdateRequest(BaseModel):
    """更新投递记录（所有字段可选——只传要改的）"""
    company: str | None = None
    position: str | None = None
    jd_text: str | None = None
    match_score: str | None = None
    match_summary: str | None = None
    status: str | None = None       # applied / screening / interviewing / offered / rejected
    applied_at: str | None = None
    notes: str | None = None


class ApplicationResponse(BaseModel):
    """投递记录响应"""
    id: int
    user_id: int
    company: str
    position: str
    jd_text: str | None = None
    match_score: str | None = None
    match_summary: str | None = None
    status: str
    applied_at: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
