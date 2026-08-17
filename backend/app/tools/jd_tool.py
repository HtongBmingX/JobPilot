from backend.app.schemas.jd import JDAnalyzeRequest
from backend.app.services.jd_service import JDService
from backend.app.tools.base_tool import BaseTool


class JDTool(BaseTool):
    """
    JD 分析 Tool
    """

    name = "jd"

    description = "分析岗位 JD"

    parameters = [
        "jd",
    ]

    def __init__(self, llm=None):
        self.service = JDService()
        if llm:
            self.service.llm = llm

    def run(self, **kwargs) -> str:
        """
        执行 JD 分析
        """

        request = JDAnalyzeRequest(
            jd=kwargs["jd"],
        )

        return self.service.analyze(request)