from backend.app.agent.jobpilot_agent import JobPilotAgent
from backend.app.tools.registry import ToolRegistry
from backend.app.tools.resume_tool import ResumeTool
from backend.app.tools.jd_tool import JDTool
from backend.app.tools.match_tool import MatchTool


def main():

    registry = ToolRegistry()

    registry.register(ResumeTool())
    registry.register(JDTool())
    registry.register(MatchTool())

    agent = JobPilotAgent(registry)

    result = agent.execute(
        """
        帮我分析这份简历：熟悉Python、FastAPI。
并分析这个JD：要求Python、3年经验。
最后做匹配评估
        """
    )

    print(result)


if __name__ == "__main__":
    main()