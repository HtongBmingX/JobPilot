"""
GET /status 路由 — 系统状态快照

依赖请求级别的 Token 和限流上下文 → 放到 main.py 里实现
这里只放 status 端点本身
"""

from fastapi import APIRouter, Depends
from backend.app.core.auth import get_current_user
from backend.app.models.user import User

status_router = APIRouter()


@status_router.get("/status")
async def get_status(
    current_user: User = Depends(get_current_user),
):
    """
    返回当前系统状态快照，前端定时拉取。

    返回字段由 _build_status 函数在 main.py 中拼接，
    因为需要访问 main 级变量（agent registry、redis client、rate limiter 等）
    """
    pass  # 实际实现在 main.py 中路由直接绑到 app 上——FastAPI 直接用 Depends 即可
