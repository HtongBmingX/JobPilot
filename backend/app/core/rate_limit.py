"""
API 限流中间件（固定窗口算法）

为什么需要限流？
- DeepSeek API 按 token 计费，无限制调用会导致费用失控
- 用户故意或意外的大量请求（脚本、刷新页面）需要拦截
- 面试价值：限流是后端生产化必备能力，面试高频考点

为什么是固定窗口而不是滑动窗口？
- 固定窗口：INCR + EXPIRE，最简单，2 条 Redis 命令，O(1)
- 滑动窗口：ZSET + ZREMRANGEBYSCORE，更精确但更复杂，O(log N)
- 当前场景（限制每分钟请求数），固定窗口完全够用
  - 误判代价低（最多在第 61 秒解除拦截）
  - 代码简单，出 bug 概率低

为什么限流基于 IP 而不是 user？
- 还没有用户系统（Phase 3 之后的 Step 3.2）
- IP 是前端代理后的真实地址（从 X-Forwarded-For 头读取）
- 以后引入用户系统后，优先基于 user_id 限流

Redis 不可用时怎么办？
- 返回 None（不限流），让请求通过
- 不阻塞正常功能——安全是有代价的，但可用性优先
"""

import functools
from fastapi import Request
from backend.app.core.redis_client import get_client
from backend.app.core.logger import logger

# 默认限流配置
DEFAULT_RATE = 20       # 每分钟最多 20 次请求
DEFAULT_WINDOW = 60     # 窗口大小（秒）


def check_rate_limit(
    key: str,
    max_requests: int = DEFAULT_RATE,
    window_seconds: int = DEFAULT_WINDOW,
) -> bool:
    """
    固定窗口限流检查。

    :param key: 限流 key（如 "rate_limit:127.0.0.1"）
    :param max_requests: 窗口内允许的最大请求数
    :param window_seconds: 窗口大小（秒）
    :return: True = 允许通过，False = 被限流

    算法：
    1. INCR key → 原子计数器 +1
    2. 如果是第一次（INCR 返回 1），设置 EXPIRE key window_seconds
    3. 如果计数 > max_requests，拒绝

    为什么 INCR 和 EXPIRE 分开发？
    Redis 的 SET 命令不支持「不存在时 SET + EXPIRE」的原子操作
    （SETNX 只做条件 SET，不能同时做 INCR）。
    """
    redis_client = get_client()
    if redis_client is None:
        # Redis 不可用——不限流，让请求通过
        return True

    try:
        current = redis_client.incr(key)
        if current == 1:
            redis_client.expire(key, window_seconds)

        allowed = current <= max_requests
        if not allowed:
            logger.warning(f"限流触发：{key}（{current}/{max_requests}）")
        return allowed
    except Exception as e:
        logger.error(f"限流检查异常：{e}，放行请求")
        # Redis 异常时放行——宁可被刷也不误杀
        return True


def get_client_ip(request: Request) -> str:
    """从请求中提取客户端 IP（优先 X-Forwarded-For，其次 request.client）"""
    client_ip = (
        request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or (request.client.host if request.client else "")
        or "unknown"
    )
    return client_ip


def rate_limit(
    max_requests: int = DEFAULT_RATE,
    window_seconds: int = DEFAULT_WINDOW,
):
    """
    FastAPI 依赖注入装饰器：给端点加限流。

    用法：
        @app.post("/agent/run")
        def agent_run(req: AgentRunRequest, _rate=Depends(rate_limit(20))):
            ...

    为什么用 Depends 而不是装饰器？
    - FastAPI 的 Depends 是声明式依赖注入——在 Swagger 文档中可见
    - 装饰器（@rate_limit）是隐式的——调用方不知道有限流
    - Depends 可以在测试中用 dependency_overrides 替换

    限流 Key 格式：rate_limit:<IP>:<endpoint>
    例如：rate_limit:127.0.0.1:/agent/run
    不同端点的限流额度独立——用户可以在 /agent/run 用完后
    仍能访问 /upload。
    """

    async def limiter(request: Request) -> None:
        # 获取客户端 IP（优先从 X-Forwarded-For 头读取）
        client_ip = get_client_ip(request)

        endpoint = request.url.path
        key = f"rate_limit:{client_ip}:{endpoint}"

        if not check_rate_limit(key, max_requests, window_seconds):
            # 被限流——抛出 429
            from fastapi import HTTPException
            raise HTTPException(
                status_code=429,
                detail=f"请求过于频繁，请 {window_seconds} 秒后重试",
            )

    return limiter
