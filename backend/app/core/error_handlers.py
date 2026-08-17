"""
FastAPI 全局错误处理器（error_handlers.py）

为什么需要全局异常处理，但不同于上次的 @app.exception_handler(Exception)？

上次的教训：全局 handler 捕获所有 Exception，包括 CORS 中间件的 OPTIONS 请求。
这次用 app.add_exception_handler() 注册在 CORS 之后，并且只在业务异常时介入。

设计原则：
1. 自定义异常：返回对应 status_code + JSON
2. 未知异常：返回 500 + 不暴露内部细节的安全错误信息
3. 不影响中间件：CORS 和 OPTIONS 正常流转
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from backend.app.core.exceptions import JobPilotError
from backend.app.core.logger import logger


def register_error_handlers(app: FastAPI) -> None:
    """
    注册所有异常处理器到 FastAPI app 实例。

    为什么抽成独立函数而不是在 main.py 里注册？
    - main.py 已经很厚了，这十几个 handler 会占据大量空间
    - 独立模块方便测试（可以导入并在测试中用 TestClient 验证错误响应格式）
    - 面试时可以说「错误处理是可插拔的——如果有新的错误类型，只需在这里加一个 handler」
    """

    @app.exception_handler(JobPilotError)
    async def jobpilot_error_handler(request: Request, exc: JobPilotError):
        """JobPilot 自定义异常 → 返回对应的 status_code + JSON"""
        logger.error(
            f"[{exc.code}] {exc.message} | path={request.url.path}",
            exc_info=True,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.code,
                "message": exc.message,
                "detail": exc.message,  # 兼容前端读取 detail 字段
            },
        )

    @app.exception_handler(Exception)
    async def unknown_error_handler(request: Request, exc: Exception):
        """
        兜底捕获未知异常。
        注意：这个 handler 在 CORS 中间件之后注册，
        OPTIONS 请求不会被拦截（中间件在 handler 之前处理）。

        返回的 message 不暴露内部细节——这是生产级安全要求。
        """
        logger.error(
            f"未捕获异常 | path={request.url.path} | {type(exc).__name__}: {exc}",
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "INTERNAL_ERROR",
                "message": "服务器内部错误，请稍后重试",
                "detail": "服务器内部错误，请稍后重试",
            },
        )
