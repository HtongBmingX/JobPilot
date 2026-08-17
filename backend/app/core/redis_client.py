"""
Redis 客户端封装

为什么需要封装一层而不是直接用 redis.Redis()？

1. 连接池管理：创建连接是有成本的——Redis 连接涉及 TCP 握手和认证。
   连接池在应用启动时创建一次，所有请求复用同一批连接，避免每次请求都
   重新建立连接。这在不使用连接池时可能导致上千个连接耗尽 Redis 的连接上限。

2. 序列化单例：整个应用共享一个 Redis 客户端实例。Python 模块级别的
   单例是懒加载的（第一次 import 时才初始化），天然线程安全。

3. 健康检查与优雅降级：Redis 不可用时不应该让整个应用崩掉。
   ping() 用于启动时检查；get_client() 返回 None 时调用方走内存 fallback。

4. 面试价值：Redis 连接管理是后端面试的常见考点。
   - "为什么用连接池？" → 避免频繁 TCP 握手，减少延迟和资源消耗
   - "连接池该多大？" → 取决于并发请求数，uvicorn workers × 并发
   - "hiredis 是什么？" → Redis 协议的 C 解析器，比纯 Python 解析快 10 倍
"""

import redis
from redis import ConnectionPool
from backend.app.core.config import settings
from backend.app.core.logger import logger


# Redis — 默认连接配置（从环境变量读取）
REDIS_HOST = getattr(settings, 'REDIS_HOST', 'localhost')
REDIS_PORT = int(getattr(settings, 'REDIS_PORT', 6379))
REDIS_DB = int(getattr(settings, 'REDIS_DB', 0))
REDIS_PASSWORD = getattr(settings, 'REDIS_PASSWORD', None)
REDIS_MAX_CONNECTIONS = int(getattr(settings, 'REDIS_MAX_CONNECTIONS', 20))

# 连接池 — 应用级单例，懒加载
# 为什么用模块级变量而不是类属性？
# Python 模块在解释器生命周期内只导入一次，模块级变量天然是单例。
# 不需要额外的 __new__ 或 metaclass。
_pool: ConnectionPool | None = None
_client: redis.Redis | None = None


def get_pool() -> ConnectionPool:
    """获取 Redis 连接池（懒加载，首次调用时创建）"""
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            password=REDIS_PASSWORD,
            max_connections=REDIS_MAX_CONNECTIONS,
            decode_responses=True,    # 自动把 bytes → str，不用手动 decode
            socket_timeout=5,         # 5 秒超时——不无限等待
            socket_connect_timeout=3,  # 3 秒连接超时
        )
        logger.info(f"Redis 连接池已创建：{REDIS_HOST}:{REDIS_PORT}")
    return _pool


def get_client() -> redis.Redis | None:
    """
    获取 Redis 客户端实例。

    返回 None 表示 Redis 不可用——调用方应走内存 fallback。
    设计决策：不抛异常，而是返回 None。为什么？
    - Redis 是缓存/持久化增强，不是核心功能（Agent 不依赖它也能跑）
    - 如果 Redis 挂了，应用应该继续服务（用内存），而不是整体崩溃
    - 这是优雅降级的核心理念
    """
    global _client
    if _client is not None:
        return _client

    try:
        pool = get_pool()
        _client = redis.Redis(connection_pool=pool)
        _client.ping()
        logger.info("Redis 连接成功")
        return _client
    except redis.ConnectionError as e:
        logger.error(f"Redis 连接失败：{e}，将降级到内存存储")
        _client = None
        return None
    except Exception as e:
        logger.error(f"Redis 初始化异常：{e}")
        _client = None
        return None


def close_redis() -> None:
    """关闭 Redis 连接（应用退出时调用）"""
    global _client, _pool
    if _client:
        try:
            _client.close()
        except Exception:
            pass
        _client = None
    if _pool:
        try:
            _pool.disconnect()
        except Exception:
            pass
        _pool = None
    logger.info("Redis 连接已关闭")
