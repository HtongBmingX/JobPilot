from backend.app.schemas.match import MatchRequest
from backend.app.services.base_service import BaseService


class MatchService(BaseService):

    def analyze(
        self,
        request: MatchRequest,
    ) -> str:
        return self._chat(
            "match_analyze",
            resume_analysis=request.resume_analysis,
            jd_analysis=request.jd_analysis,
        )