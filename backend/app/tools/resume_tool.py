from backend.app.schemas.resume import ResumeAnalyzeRequest
from backend.app.services.resume_service import ResumeService
from backend.app.tools.base_tool import BaseTool
from backend.app.tools.registry import ToolRegistry


class ResumeTool(BaseTool):
    """
    简历分析 Tool
    """

    name = "resume"

    description = "分析用户简历"

    parameters = [
        "resume",
    ]

    def __init__(self, llm=None):
        self.service = ResumeService()
        if llm:
            self.service.llm = llm  # 共享 agent 的 LLMService 实例

    def run(self, **kwargs) -> str:

        request = ResumeAnalyzeRequest(
            resume=kwargs["resume"],
        )

        return self.service.analyze(request)


# registry = ToolRegistry()
#
# registry.register(
#     ResumeTool()
# )
#
# print(registry.list_tools())
# tool = registry.get("resume")
#
# result = tool.run(
#     resume="""
# 软件工程专业本科生
# 熟悉 Python、C++、FastAPI
# """
# )
#
# print(result)