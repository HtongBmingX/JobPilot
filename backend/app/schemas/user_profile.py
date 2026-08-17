"""用户画像 Pydantic schemas"""

from pydantic import BaseModel
from datetime import datetime


class UserProfileUpdateRequest(BaseModel):
    """更新画像（所有字段可选）"""
    tech_stack: str | None = None
    target_role: str | None = None
    target_companies: str | None = None
    education: str | None = None
    experience_summary: str | None = None


class UserProfileResponse(BaseModel):
    """画像响应"""
    id: int
    user_id: int
    tech_stack: str | None = None
    target_role: str | None = None
    target_companies: str | None = None
    education: str | None = None
    experience_summary: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
