"""
对话摘要器 — 把早期对话压缩成摘要，替代直接丢弃。

为什么需要摘要压缩？
- 纯截断（TokenBudget.fit_history）会把超出配额的早期消息直接丢掉，
  长对话时 Agent 会"失忆"——完全不记得之前聊过什么。
- 摘要压缩用 LLM 把早期对话总结成一段要点，信息有损但保留核心，
  Agent 仍然"记得"大概聊了什么。

设计：只压缩"被截断掉的部分"，近期对话保持原文（近期细节更重要）。
"""

from backend.app.prompts.prompt_manager import PromptManager
from backend.app.services.llm_service import LLMService
from backend.app.core.logger import logger


class ConversationSummarizer:
    """把一段对话历史压缩成摘要"""

    def __init__(self, llm: LLMService | None = None):
        self.prompt_manager = PromptManager()
        self.llm = llm or LLMService()

    def summarize(self, conversation_text: str) -> str:
        """把对话文本压缩成一段摘要"""
        if not conversation_text or not conversation_text.strip():
            return ""

        user_prompt = self.prompt_manager.render_prompt(
            "summarize",
            conversation=conversation_text,
        )
        try:
            result = self.llm.chat(
                system_prompt="你是对话摘要助手。",
                user_prompt=user_prompt,
            )
            return result.content.strip()
        except Exception as e:
            logger.warning(f"对话摘要失败：{e}，降级为截断")
            return ""
