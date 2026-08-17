"""
Redis 版会话存储

用 Redis 替代内存 dict 存 Session 数据。

为什么要从内存 dict 迁移到 Redis？
1. 持久化：服务重启后会话不丢失（当前 dict 在重启后清空）
2. 多进程共享：uvicorn workers > 1 时，内存 dict 不能跨进程共享
3. TTL 自动过期：Redis 的 EXPIRE 机制自动清理过期会话（内存 dict 做不到）
4. 面试价值：会话管理是后端基础能力——内存 → Redis 的迁移路径体现工程意识

接口设计：完全兼容旧的 MemoryManager（create_session / get_session / delete_session），
只是后端从 dict 换成了 Redis。调用方（JobPilotAgent）一行代码不用改。

序列化方案：SessionMemory → asdict() → json.dumps() → Redis (String)
为什么不用 Redis Hash？
- String 方案最简单：一个 key 存整个 session，读写各一次命令
- Hash 方案更省内存但更复杂：每个字段一个 hash field，更新时只改一个字段
- 当前 session 数据大小（几 KB），String 方案完全够用
- 未来如果需要部分更新（如只更新 match_result 不重写整个 session），再迁到 Hash
"""

import json
from backend.app.memory.session_memory import SessionMemory
from backend.app.core.redis_client import get_client
from backend.app.core.logger import logger

# Redis key 前缀（避免和项目其他 key 冲突）
SESSION_PREFIX = "jobpilot:session:"

# 会话过期时间（秒）—— 24 小时后自动清理
SESSION_TTL = 24 * 60 * 60


class RedisSessionStore:
    """
    Redis 版会话存储。

    使用方式：
        store = RedisSessionStore()
        session = store.create_session("user-123")  # 新建或获取已有会话

    如果 Redis 不可用，所有方法返回 None/空值，
    调用方（MemoryManager）会 fallback 到内存。
    """

    def __init__(self):
        self.redis = get_client()
        self._available = self.redis is not None

    def is_available(self) -> bool:
        """Redis 是否可用。调方用此判断是否走内存 fallback。"""
        return self._available

    def _key(self, session_id: str) -> str:
        """拼接 Redis key"""
        return f"{SESSION_PREFIX}{session_id}"

    def create_session(self, session_id: str) -> SessionMemory | None:
        """
        创建或获取已有会话。

        Redis 中如果已存在相同 session_id，返回已有会话；
        否则创建新会话并存入 Redis。
        """
        if not self._available:
            return None

        existing = self.get_session(session_id)
        if existing:
            return existing

        session = SessionMemory()
        self._save(session_id, session)
        return session

    def get_session(self, session_id: str) -> SessionMemory | None:
        """获取会话。不存在返回 None。"""
        if not self._available:
            return None

        key = self._key(session_id)
        try:
            raw = self.redis.get(key)
            if raw is None:
                return None
            data = json.loads(raw)
            return SessionMemory.from_dict(data)
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"Redis 会话数据损坏：{session_id} | {e}")
            # 删除损坏的数据，下次请求重新创建
            self.redis.delete(key)
            return None

    def save_session(self, session_id: str, session: SessionMemory) -> bool:
        """保存（更新）会话到 Redis。成功返回 True。"""
        return self._save(session_id, session)

    def _save(self, session_id: str, session: SessionMemory) -> bool:
        if not self._available:
            return False

        key = self._key(session_id)
        try:
            data = json.dumps(session.to_dict(), ensure_ascii=False)
            # set(key, value, ex=ttl) 是新推荐写法（setex 已废弃）
            self.redis.set(key, data, ex=SESSION_TTL)
            return True
        except Exception as e:
            logger.error(f"Redis 保存会话失败：{session_id} | {e}")
            return False

    def delete_session(self, session_id: str) -> None:
        """删除会话。不存在不报错。"""
        if not self._available:
            return

        key = self._key(session_id)
        try:
            self.redis.delete(key)
        except Exception as e:
            logger.error(f"Redis 删除会话失败：{session_id} | {e}")
