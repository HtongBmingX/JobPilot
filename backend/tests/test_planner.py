from backend.app.agent.planner import Planner
from backend.app.tools.registry import ToolRegistry
from backend.app.tools.resume_tool import ResumeTool
from backend.app.tools.jd_tool import JDTool
from backend.app.tools.match_tool import MatchTool


def main():
    registry = ToolRegistry()

    registry.register(ResumeTool())
    registry.register(JDTool())
    registry.register(MatchTool())

    planner = Planner()

    query = """
请分析下面这份简历：

姓名：张三

学历：
大连理工大学 软件工程专业 本科

专业技能：
- 熟悉 Python、C++、MySQL
- 熟悉 FastAPI 开发
- 熟悉 Git
- 了解深度学习基础
- 了解 Agent 开发

项目经历：
JobPilot 智能求职 Agent
- 基于 FastAPI 开发后端
- 实现 PromptManager
- 实现 Resume/JD/Match 三个 Tool
- 实现 Planner、Memory、Tool Registry
- 使用 DeepSeek API 完成 LLM 调用

求职意向：
AI Agent 开发工程师
"""

    plan = planner.think(
        query=query,
        tools=registry.build_prompt(),
    )

    print("\n===== Planner 输出 =====")
    print(plan)
    print("=======================\n")


if __name__ == "__main__":
    main()