"""
会话管理器（支持 Redis + 内存 fallback）

Phase 3 升级：优先使用 Redis 存储会话，Redis 不可用时自动 fallback 到内存。

接口保持不变：create_session / get_session / delete_session
调用方（JobPilotAgent）一行代码不用改。

设计原则：
1. 透明切换：调用方不感知存储后端是 Redis 还是内存
2. 优雅降级：Redis 挂了不影响核心功能（Agent 继续运行）
3. 接口兼容：和旧 MemoryManager 完全相同的公共接口
"""

from backend.app.memory.session_memory import SessionMemory
from backend.app.memory.redis_store import RedisSessionStore
from backend.app.core.logger import logger


class MemoryManager:
    """
    会话管理器。

    Phase 3 改造后：
    - 自动检测 Redis 是否可用
    - 可用时用 Redis（持久化 + 多进程共享 + TTL 自动过期）
    - 不可用时 fallback 到内存 dict（功能正常，但重启丢数据）
    """

    def __init__(self):
        # 内存 fallback
        self._sessions: dict[str, SessionMemory] = {}
        # Redis 存储（可能不可用）
        self._redis_store = RedisSessionStore()

        backend = "Redis" if self._redis_store.is_available() else "内存 dict"
        logger.info(f"MemoryManager 初始化完成，存储后端：{backend}")

    def create_session(self, session_id: str) -> SessionMemory:
        """
        创建或获取已有会话。

        如果 Session 已存在，直接返回（无论来自 Redis 还是内存）。
        """
        # 1. 先尝试 Redis
        if self._redis_store.is_available():
            existing = self._redis_store.get_session(session_id)
            if existing:
                return existing
            # 不存在 → 创建并存入 Redis
            memory = SessionMemory()
            self._redis_store.save_session(session_id, memory)
            return memory

        # 2. 内存 fallback
        if session_id in self._sessions:
            return self._sessions[session_id]

        memory = SessionMemory()
        self._sessions[session_id] = memory
        return memory

    def get_session(self, session_id: str) -> SessionMemory:
        """
        获取指定 Session。

        如果 Session 不存在，抛出 KeyError。
        """
        # 1. 先尝试 Redis
        if self._redis_store.is_available():
            session = self._redis_store.get_session(session_id)
            if session:
                return session
            raise KeyError(f"Session '{session_id}' not found.")

        # 2. 内存 fallback
        if session_id not in self._sessions:
            raise KeyError(f"Session '{session_id}' not found.")
        return self._sessions[session_id]

    def save_session(self, session_id: str, memory: SessionMemory) -> None:
        """
        更新会话数据。

        Agent 执行完毕后调用，把最新状态持久化。
        """
        # 1. 先尝试 Redis
        if self._redis_store.is_available():
            self._redis_store.save_session(session_id, memory)
            return

        # 2. 内存 fallback
        self._sessions[session_id] = memory

    def delete_session(self, session_id: str) -> None:
        """
        删除指定 Session。如果不存在，不报错。
        """
        if self._redis_store.is_available():
            self._redis_store.delete_session(session_id)

        self._sessions.pop(session_id, None)

    def clear(self) -> None:
        """
        清空所有 Session。
        注意：Redis 模式下只清内存缓存，不清 Redis（需要逐个删除）。
        """
        self._sessions.clear()
        # Redis 清空需要 scan + delete 遍历，过于耗时且不常用，不实现
        logger.warning(
            "clear() 仅清空内存缓存。如需清空 Redis 会话，请手动执行："
            f"redis-cli KEYS '{'jobpilot:session:*'}' | xargs redis-cli DEL"
        )
