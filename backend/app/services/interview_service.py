"""面试服务"""

from backend.app.services.base_service import BaseService


class InterviewService(BaseService):

    def interview(
        self,
        resume_analysis: str,
        jd_analysis: str,
        mode: str,
        round_number: int,
        instruction: str,
        conversation_history: str,
    ) -> str:
        """执行一轮面试"""
        return self._chat(
            "interview",
            resume_analysis=resume_analysis,
            jd_analysis=jd_analysis,
            mode=mode,
            round_number=str(round_number),
            instruction=instruction,
            conversation_history=conversation_history,
        )
