from backend.app.schemas.resume import ResumeAnalyzeRequest
from backend.app.services.base_service import BaseService


class ResumeService(BaseService):

    def analyze(
        self,
        request: ResumeAnalyzeRequest,
    ) -> str:

        return self._chat(
            "resume_analyze",
            resume=request.resume,
        )