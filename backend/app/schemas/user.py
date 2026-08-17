"""用户相关 Pydantic 请求/响应模型"""

from pydantic import BaseModel, Field


class UserRegisterRequest(BaseModel):
    """注册请求"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, max_length=128, description="密码")


class UserLoginRequest(BaseModel):
    """登录请求"""
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class UserResponse(BaseModel):
    """用户信息响应"""
    id: int
    username: str

    model_config = {"from_attributes": True}  # 支持从 ORM 对象直接转换
