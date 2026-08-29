"""
MemoryManager 单测（断言式，强制走内存 fallback，不碰 Redis）

MemoryManager 优先 Redis、不可用时 fallback 到内存 dict。
测试里通过替换 _redis_store 为一个「不可用」的假 store，
强制走内存路径，验证 create/get/save/delete/clear 的核心逻辑，
且不依赖本机是否装了 Redis。
"""

from unittest.mock import MagicMock
from backend.app.memory.memory_manager import MemoryManager


def _manager_without_redis() -> MemoryManager:
    """构造一个 Redis 不可用的 MemoryManager（强制内存 fallback）"""
    manager = MemoryManager.__new__(MemoryManager)  # 绕过 __init__ 里的真实 Redis 探测
    manager._sessions = {}
    manager._redis_store = MagicMock()
    manager._redis_store.is_available.return_value = False
    return manager


def test_create_and_get_session():
    manager = _manager_without_redis()
    session = manager.create_session("user001")
    session.resume = "张三的简历"
    # 再次获取同一 session，应拿到同一对象
    assert manager.get_session("user001") is session
    assert manager.get_session("user001").resume == "张三的简历"


def test_sessions_are_isolated():
    manager = _manager_without_redis()
    s1 = manager.create_session("user001")
    s2 = manager.create_session("user002")
    s1.resume = "张三"
    s2.resume = "李四"
    assert manager.get_session("user001").resume == "张三"
    assert manager.get_session("user002").resume == "李四"


def test_get_missing_session_raises_keyerror():
    manager = _manager_without_redis()
    try:
        manager.get_session("不存在")
        assert False, "应当抛出 KeyError"
    except KeyError:
        pass


def test_save_session_updates():
    manager = _manager_without_redis()
    session = manager.create_session("user001")
    session.resume = "旧简历"
    manager.save_session("user001", session)
    session.resume = "新简历"
    manager.save_session("user001", session)
    assert manager.get_session("user001").resume == "新简历"


def test_delete_session():
    manager = _manager_without_redis()
    manager.create_session("user001")
    manager.delete_session("user001")
    try:
        manager.get_session("user001")
        assert False, "删除后应 KeyError"
    except KeyError:
        pass
    # 删除不存在的 session 不报错
    manager.delete_session("不存在")


def test_clear():
    manager = _manager_without_redis()
    manager.create_session("user001")
    manager.create_session("user002")
    manager.clear()
    assert manager._sessions == {}
