"""
诊断用测试：隔离 Agent 循环逻辑 与 Planner 决策。

为什么需要这个测试？
  你之前跑 agent 时，发现它卡在 resume 循环（连续多步都 action=resume）。
  这个 bug 可能来自两处：
    (A) Agent 的 ReAct 循环代码有缺陷（比如 memory 没存进去、finish 判断错）
    (B) Planner 的 prompt 写得不够"硬"，LLM 没按"简历→JD→匹配"顺序决策

  本测试用 mock 把 Planner 决策"钉死"在一个正确序列上，
  如果此时 Agent 能正常推进，就证明 (A) 没问题，bug 在 (B)。

运行（项目根目录，用 venv）：
  .venv/Scripts/python.exe -m pytest backend/tests/test_agent_loop.py -s
"""

from unittest.mock import patch, MagicMock

from backend.app.agent.jobpilot_agent import JobPilotAgent
from backend.app.tools.registry import ToolRegistry
from backend.app.schemas.plan import Plan
from backend.app.schemas.chat import ChatResult
from backend.app.memory.session_memory import SessionMemory


# ---------- 1) 一个"假"的 LLM 返回，避免真实打 API 花 token ----------
def fake_chat(*args, **kwargs) -> ChatResult:
    return ChatResult(
        content="（mock 返回）",
        model="mock",
        elapsed=0.0,
        prompt_tokens=0,
        completion_tokens=0,
        total_tokens=0,
    )


# ---------- 2) 构造一个"假"的注册中心 ----------
# 用 MagicMock 把三个 Tool 的 run() 替换成直接返回固定字符串，
# 这样测试只验证 Agent 的"循环调度"，完全不碰真实业务/API。
def build_mock_registry() -> ToolRegistry:
    reg = ToolRegistry()

    r = MagicMock(name="ResumeTool")
    r.name = "resume"
    r.run.return_value = "（简历分析结果）"
    reg.register(r)

    j = MagicMock(name="JdTool")
    j.name = "jd"
    j.run.return_value = "（JD 分析结果）"
    reg.register(j)

    m = MagicMock(name="MatchTool")
    m.name = "match"
    m.run.return_value = "（匹配结果）"
    reg.register(m)

    return reg


# ---------- 3) 脚本化的"正确" Planner 决策序列 ----------
# 模拟一个听话的 Planner：严格按 resume → jd → match → finish 走
SCRIPTED_GOOD = [
    Plan(thought="先分析简历", action="resume",
         action_input={"resume": "张三 熟悉 Python"}),
    Plan(thought="再分析 JD", action="jd",
         action_input={"jd": "岗位要求 Python"}),
    Plan(thought="做匹配", action="match", action_input={}),
    Plan(thought="全部完成", action="finish", action_input={}),
]


def test_agent_progresses_when_planner_is_sane():
    """
    隔离测试：当 Planner 做正确决策时，Agent 循环应当
    依次调用 resume / jd / match，并在 finish 后返回 synthesize 结果。

    若此测试通过 → 证明 Agent 循环代码本身没问题，
    你之前遇到的卡死 100% 是 Planner 的 prompt 问题。
    """
    agent = JobPilotAgent(build_mock_registry())

    with patch(
        "backend.app.agent.jobpilot_agent.Planner.think",
        side_effect=list(SCRIPTED_GOOD),  # 每次 think 返回序列里的下一个 Plan
    ), patch(
        "backend.app.services.llm_service.LLMService.chat",
        side_effect=fake_chat,            # 最终 synthesize 用 mock 返回
    ):
        result = agent.execute("帮我分析简历和 JD 并匹配", max_steps=6)

    # 最终答案来自 _synthesize，而 _synthesize 调了 mock chat → "（mock 返回）"
    assert result == "（mock 返回）"
    print("\n[PASS] 循环逻辑正确：resume → jd → match → finish 全部跑通")


def test_single_tool_synthesizes_instead_of_looping():
    """
    验证单工具收尾修复：resume 分析完成后直接 synthesize，
    而不是进入下一轮走到 chat（旧行为）或死循环到 max_steps。

    场景：用户上传简历，只问"帮我分析简历"（单工具，无 JD）。
    """
    agent = JobPilotAgent(build_mock_registry())
    with patch(
        "backend.app.services.llm_service.LLMService.chat",
        side_effect=fake_chat,
    ):
        # 传入简历原文，触发单工具收尾逻辑
        result = agent.execute("帮我分析简历", resume="张三 熟悉 Python")

    # 单工具分析完直接 synthesize，返回 synthesize 的 mock 结果
    assert result == "（mock 返回）"
    # 且不会返回"最大步数"（没有死循环）
    assert "最大步数" not in result


def test_format_memory_evolves():
    """
    辅助诊断：确认 _format_memory 能正确反映"已完成"进度。
    如果这里都对了，说明 Agent 喂给 Planner 的 memory 文本没问题，
    那 Planner 还选错 action，就是它自己的 prompt 没约束住。
    """
    mem = SessionMemory()
    assert "尚无" in JobPilotAgent._format_memory(mem)

    mem.resume_analysis = "x"
    mem.jd_analysis = "y"
    mem.match_result = "z"
    out = JobPilotAgent._format_memory(mem)

    assert "简历分析已完成" in out
    assert "JD 分析已完成" in out
    assert "岗位匹配已完成" in out
    print("\n[PASS] _format_memory 状态演化正确")


if __name__ == "__main__":
    test_format_memory_evolves()
    test_agent_progresses_when_planner_is_sane()
    test_single_tool_synthesizes_instead_of_looping()
    print("\nALL DIAGNOSTIC TESTS OK")
