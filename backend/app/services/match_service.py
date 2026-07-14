from backend.app.schemas.match import MatchRequest
from backend.app.services.base_service import BaseService


class MatchService(BaseService):

    def analyze(
        self,
        request: MatchRequest,
    ) -> str:
        return self._chat(
            "match_analyze",
            resume_analyze = request.resume_analysis,
            jd_analyze = request.jd_analysis,
        )