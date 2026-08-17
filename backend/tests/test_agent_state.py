"""
AgentStateMachine 状态机测试（断言式）

这是 Agent 最核心的决策逻辑，之前踩过两个严重 bug：
1. _query_mentions_jd 空函数体
2. wants_resume/wants_jd NameError

所以这里用断言式测试把状态机的关键路由规则锁死，防止回归。
"""

from backend.app.agent.agent_state import (
    AgentStateMachine,
    _query_mentions_resume,
    _query_mentions_jd,
    _query_mentions_interview,
    _query_mentions_match,
    _query_mentions_knowledge,
    _query_mentions_end_interview,
)
from backend.app.memory.session_memory import SessionMemory


# ============================================================
#  关键词检测函数
# ============================================================

def test_mentions_resume():
    assert _query_mentions_resume("帮我分析简历") is True
    assert _query_mentions_resume("看看我的技能") is True
    # 收窄后"求职"不应再命中简历
    assert _query_mentions_resume("我想求职后端") is False


def test_mentions_jd():
    assert _query_mentions_jd("分析这个 JD") is True
    assert _query_mentions_jd("看看岗位要求") is True
    # 去掉"角色"后不应命中
    assert _query_mentions_jd("这个角色是什么") is False


def test_mentions_interview():
    assert _query_mentions_interview("帮我面试") is True
    assert _query_mentions_interview("模拟面试") is True


def test_mentions_match():
    assert _query_mentions_match("帮我匹配") is True
    assert _query_mentions_match("我和这个岗位匹配吗") is True
    assert _query_mentions_match("帮我分析简历") is False


def test_mentions_knowledge():
    assert _query_mentions_knowledge("后端面试一般问什么") is True
    assert _query_mentions_knowledge("怎么准备面试") is True
    # 去掉"知识/技巧"后不应命中
    assert _query_mentions_knowledge("这个知识点") is False


def test_mentions_knowledge_what_is():
    """「什么是」和「是什么」两种中文语序都要命中知识库"""
    assert _query_mentions_knowledge("什么是 ReAct 模式") is True
    assert _query_mentions_knowledge("MySQL 索引是什么") is True


def test_mentions_end_interview():
    assert _query_mentions_end_interview("结束面试") is True
    assert _query_mentions_end_interview("帮我面试") is False


# ============================================================
#  状态机路由规则
# ============================================================

def test_initial_resume_analysis():
    """空状态 + 问简历 → 允许 resume"""
    memory = SessionMemory()
    allowed = AgentStateMachine.compute_allowed_actions(memory, "帮我分析简历")
    assert "resume" in allowed


def test_initial_jd_analysis():
    """空状态 + 问 JD → 允许 jd"""
    memory = SessionMemory()
    allowed = AgentStateMachine.compute_allowed_actions(memory, "分析这个 JD")
    assert "jd" in allowed


def test_match_requires_both_done():
    """简历和 JD 都分析完 + 问匹配 → 允许 match"""
    memory = SessionMemory()
    memory.resume_analysis = "简历分析结果"
    memory.jd_analysis = "JD 分析结果"
    allowed = AgentStateMachine.compute_allowed_actions(memory, "帮我匹配")
    assert "match" in allowed


def test_match_not_allowed_when_not_done():
    """简历/JD 未分析完 + 问匹配 → 不允许 match"""
    memory = SessionMemory()
    allowed = AgentStateMachine.compute_allowed_actions(memory, "帮我匹配")
    assert "match" not in allowed


def test_knowledge_routes_to_search():
    """问知识库类问题 → 路由到 search"""
    memory = SessionMemory()
    allowed = AgentStateMachine.compute_allowed_actions(memory, "后端面试一般问什么")
    assert allowed == ["search"]


def test_interview_in_progress_keeps_interview():
    """面试进行中 + 用户回答（不含"面试"词）→ 继续 interview"""
    memory = SessionMemory()
    memory.interview_mode = "mixed"
    memory.interview_round = 2
    allowed = AgentStateMachine.compute_allowed_actions(memory, "我熟悉 Python")
    assert allowed == ["interview"]


def test_interview_end_returns_chat():
    """面试进行中 + 用户喊停 → 走 chat"""
    memory = SessionMemory()
    memory.interview_mode = "mixed"
    allowed = AgentStateMachine.compute_allowed_actions(memory, "结束面试")
    assert allowed == ["chat"]


def test_new_resume_invalidates_old_analysis():
    """新简历传入（resume_analysis 被清空后）→ 重新分析 resume"""
    memory = SessionMemory()
    memory.resume = "新简历内容"
    memory.resume_analysis = None  # 模拟 execute 里新简历清空旧分析的逻辑
    allowed = AgentStateMachine.compute_allowed_actions(memory, "帮我分析简历")
    assert "resume" in allowed


def test_plain_chat_when_nothing_requested():
    """无任何意图 + 无业务记忆 → chat"""
    memory = SessionMemory()
    allowed = AgentStateMachine.compute_allowed_actions(memory, "你好")
    assert allowed == ["chat"]
