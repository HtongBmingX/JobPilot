"""面试模拟 Tool"""

from backend.app.tools.base_tool import BaseTool
from backend.app.services.interview_service import InterviewService
from backend.app.core.logger import logger


class InterviewTool(BaseTool):
    name = "interview"
    description = "模拟面试：针对求职者的简历和目标岗位，扮演面试官进行技术面、行为面或综合面试"
    parameters = ["mode", "round_number", "conversation_history"]  # mode: technical/behavioral/mixed

    MODE_LABELS = {
        "technical": "技术面（深挖技术栈、底层原理、系统设计）",
        "behavioral": "行为面（团队协作、项目经历、冲突处理）",
        "mixed": "综合面（技术和行为问题交替）",
    }

    def __init__(self):
        self.service = InterviewService()

    def run(self, **kwargs) -> str:
        mode = kwargs.get("mode", "mixed")
        mode_label = self.MODE_LABELS.get(mode, self.MODE_LABELS["mixed"])

        resume = kwargs.get("resume_analysis") or "（未提供）"
        jd = kwargs.get("jd_analysis") or "（未提供）"
        round_number = kwargs.get("round_number", 1)
        conversation_history = kwargs.get("conversation_history") or "（面试即将开始）"

        # 根据轮数生成指令：第 1 轮暖场，中间轮追问，最后轮给评价
        instruction = self._instruction_for_round(round_number)

        if resume != "（未提供）" or jd != "（未提供）":
            logger.info(f"面试 Tool 收到分析结果 — 简历：{len(resume)} 字，JD：{len(jd)} 字，第 {round_number} 轮")
        else:
            logger.info(f"面试 Tool：未收到分析结果，使用通用模式，第 {round_number} 轮")

        return self.service.interview(
            resume_analysis=resume,
            jd_analysis=jd,
            mode=mode_label,
            round_number=round_number,
            instruction=instruction,
            conversation_history=conversation_history,
        )

    @staticmethod
    def _instruction_for_round(round_number: int) -> str:
        """
        根据面试轮数返回对应指令。

        设计：6 轮一个完整面试周期
        - 第 1 轮：暖场（自我介绍类，降低压力）
        - 第 2-5 轮：正式提问（深挖技术/行为）
        - 第 6 轮：收尾 + 给出整体评价
        """
        if round_number == 1:
            return "请开始面试，先用一个轻松的问题暖场（如自我介绍或简单背景了解）"
        if round_number == 6:
            return "这是最后一轮，请根据前面的回答给出整体面试评价：技术深度、表达清晰度评分（1-5 星），以及 2-3 条改进建议"
        return f"这是第 {round_number} 轮提问。请基于上一轮的回答继续追问，问题要逐步深入"
