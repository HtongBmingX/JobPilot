from backend.app.schemas.match import MatchRequest
from backend.app.services.match_service import MatchService
from backend.app.tools.base_tool import BaseTool


class MatchTool(BaseTool):
    """
    岗位匹配 Tool
    """

    name = "match"

    description = "根据简历分析结果和岗位分析结果进行匹配"

    parameters = [
        "resume_analysis",
        "jd_analysis",
    ]

    def __init__(self, llm=None):
        self.service = MatchService()
        if llm:
            self.service.llm = llm

    def run(self, **kwargs) -> str:
        """
        执行岗位匹配
        """

        request = MatchRequest(
            resume_analysis=kwargs["resume_analysis"],
            jd_analysis=kwargs["jd_analysis"],
        )

        return self.service.analyze(request)