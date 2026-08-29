"""
JobPilotAgent 主线逻辑单测（断言式，mock 隔离，不打真实 API）

和 test_agent_loop.py 的分工：
- test_agent_loop.py 测「循环调度」：Planner 决策正确时，Agent 依次跑通 resume→jd→match
- 这里测「容错主线」：追问短路、越界 action 降级、来源标注——都是之前踩过坑的真实逻辑
"""

from unittest.mock import patch, MagicMock

from backend.app.agent.jobpilot_agent import JobPilotAgent
from backend.app.tools.registry import ToolRegistry
from backend.app.schemas.plan import Plan
from backend.app.schemas.chat import ChatResult
from backend.app.memory.session_memory import SessionMemory


def _mock_llm_chat():
    """mock LLMService.chat，返回固定 ChatResult"""
    def fake_chat(*args, **kwargs):
        return ChatResult(
            content="（mock 返回）", model="mock", elapsed=0.0,
            prompt_tokens=0, completion_tokens=0, total_tokens=0,
        )
    return patch("backend.app.services.llm_service.LLMService.chat", side_effect=fake_chat)


def _agent() -> JobPilotAgent:
    registry = ToolRegistry()
    for name in ("resume", "jd", "match"):
        tool = MagicMock()
        tool.name = name
        tool.run.return_value = "（工具结果）"
        registry.register(tool)
    return JobPilotAgent(registry)


# ============================================================
#  _is_followup（追问短路）
# ============================================================

def test_is_followup_no_analysis():
    """无业务记忆 → 不是追问"""
    agent = _agent()
    assert agent._is_followup(SessionMemory(), "随便聊聊") is False


def test_is_followup_plain_question():
    """有分析结果 + 普通追问 → 是追问"""
    memory = SessionMemory()
    memory.resume_analysis = "简历分析"
    agent = _agent()
    assert agent._is_followup(memory, "能再详细说说吗") is True


def test_is_followup_new_analysis_intent():
    """有分析结果，但 query 明确要求重新分析 → 不是追问"""
    memory = SessionMemory()
    memory.resume_analysis = "旧分析"
    agent = _agent()
    assert agent._is_followup(memory, "再帮我分析一下简历") is False


def test_is_followup_in_interview():
    """面试进行中 → 不是追问（交给状态机路由到 interview）"""
    memory = SessionMemory()
    memory.resume_analysis = "简历分析"
    memory.interview_mode = "mixed"
    agent = _agent()
    assert agent._is_followup(memory, "我熟悉 Python") is False


# ============================================================
#  _prepend_sources（来源标注代码强制）
# ============================================================

def test_prepend_sources_empty():
    agent = _agent()
    assert agent._prepend_sources("回答", SessionMemory()) == "回答"


def test_prepend_sources_with_sources():
    memory = SessionMemory()
    memory.search_sources = ["后端·Redis", "后端·数据库"]
    agent = _agent()
    out = agent._prepend_sources("回答", memory)
    assert out.startswith("> 📚 参考来源：")
    assert "后端·Redis" in out
    assert "后端·数据库" in out
    assert out.endswith("回答")


# ============================================================
#  越界 action 降级（Planner 返回状态机不允许的 action）
# ============================================================

def test_illegal_action_degrades_to_synthesize():
    """
    状态机允许 resume/jd，但 mock Planner 返回 match（非法，未分析完就匹配）。
    代码应降级为直接 synthesize，而不是执行非法工具。
    """
    agent = _agent()
    illegal_plan = Plan(thought="强行匹配", action="match", action_input={})

    with patch(
        "backend.app.agent.jobpilot_agent.Planner.think",
        return_value=illegal_plan,
    ), _mock_llm_chat():
        # query 同时含简历和 JD 关键词 → 状态机 allowed = ["resume", "jd"]
        # match 不在其中 → 触发越界降级
        result = agent.execute("帮我分析简历和这个 JD", max_steps=6)

    assert result == "（mock 返回）"  # 降级走 synthesize，返回 mock chat 内容
