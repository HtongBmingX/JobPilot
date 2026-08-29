"""
SessionMemory 单测（断言式）

覆盖业务记忆/对话记忆的写入，以及 add_user_message/add_assistant_message。
序列化的深入测试在 test_session_memory_serialization.py，这里不重复。
"""

from backend.app.memory.session_memory import SessionMemory


def test_new_memory_is_empty():
    memory = SessionMemory()
    assert memory.resume is None
    assert memory.resume_analysis is None
    assert memory.messages == []
    assert memory.interview_round == 0


def test_business_memory_assignment():
    memory = SessionMemory()
    memory.resume = "软件工程简历"
    memory.resume_analysis = "Python、FastAPI"
    memory.match_result = "匹配度 80"
    assert memory.resume == "软件工程简历"
    assert memory.resume_analysis == "Python、FastAPI"
    assert memory.match_result == "匹配度 80"


def test_add_user_and_assistant_message():
    memory = SessionMemory()
    memory.add_user_message("帮我分析简历")
    memory.add_assistant_message("好的，分析结果如下...")
    assert memory.messages == [
        {"role": "user", "content": "帮我分析简历"},
        {"role": "assistant", "content": "好的，分析结果如下..."},
    ]


def test_search_sources_default_empty_list():
    """search_sources 用 default_factory，两个实例互不共享"""
    m1 = SessionMemory()
    m2 = SessionMemory()
    m1.search_sources.append("来源A")
    assert m2.search_sources == []
