from backend.app.schemas.jd import JDAnalyzeRequest
from backend.app.services.base_service import BaseService


class JDService(BaseService):

    def analyze(
        self,
        request: JDAnalyzeRequest,
    ) -> str:
        return self._chat(
            "jd_analyze",
            jd=request.jd,
        )