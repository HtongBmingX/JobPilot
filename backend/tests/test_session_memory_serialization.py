"""
SessionMemory 序列化测试（断言式）

覆盖 to_dict/from_dict 的字段完整性、旧数据兼容、user_profile 排除持久化。
"""

from backend.app.memory.session_memory import SessionMemory


def test_to_dict_and_from_dict_roundtrip():
    """序列化再反序列化，字段应完整保留"""
    memory = SessionMemory()
    memory.resume = "简历"
    memory.jd = "JD"
    memory.resume_analysis = "简历分析"
    memory.jd_analysis = "JD 分析"
    memory.match_result = "匹配结果"
    memory.search_result = "检索结果"
    memory.search_sources = ["来源1", "来源2"]
    memory.interview_mode = "mixed"
    memory.interview_round = 3
    memory.summary = "早期摘要"
    memory.summarized_count = 5
    memory.messages = [{"role": "user", "content": "你好"}]

    data = memory.to_dict()
    restored = SessionMemory.from_dict(data)

    assert restored.resume == "简历"
    assert restored.jd_analysis == "JD 分析"
    assert restored.match_result == "匹配结果"
    assert restored.search_result == "检索结果"
    assert restored.search_sources == ["来源1", "来源2"]
    assert restored.interview_mode == "mixed"
    assert restored.interview_round == 3
    assert restored.summary == "早期摘要"
    assert restored.summarized_count == 5
    assert restored.messages == [{"role": "user", "content": "你好"}]


def test_user_profile_not_persisted():
    """user_profile 属于 SQLite 长期记忆，不应进 Redis 的 to_dict"""
    memory = SessionMemory()
    memory.user_profile = "目标岗位：后端"
    data = memory.to_dict()
    assert "user_profile" not in data


def test_from_dict_compatible_with_old_data():
    """旧数据（缺新字段）能正常加载"""
    old_data = {
        "resume": "旧简历",
        "resume_analysis": "旧分析",
        "messages": [],
    }
    memory = SessionMemory.from_dict(old_data)
    # 新字段都有默认值
    assert memory.interview_mode is None
    assert memory.interview_round == 0
    assert memory.summary is None
    assert memory.search_result is None
    assert memory.search_sources == []


def test_from_dict_ignores_unknown_fields():
    """未知字段（未来版本加的）被忽略，不抛异常"""
    data = {"resume": "x", "future_field": "不知道是什么"}
    memory = SessionMemory.from_dict(data)
    assert memory.resume == "x"


def test_default_factory_messages_independent():
    """每个实例的 messages 独立（default_factory 防共享）"""
    m1 = SessionMemory()
    m2 = SessionMemory()
    m1.messages.append({"role": "user", "content": "a"})
    assert m2.messages == []
