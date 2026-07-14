from backend.app.prompts.prompt_manager import PromptManager
from backend.app.services.llm_service import LLMService


class BaseService:
    """
    所有 AI Service 的基类，
    封装 PromptManager、LLMService 和通用聊天逻辑。
    """

    def __init__(self):
        self.prompt_manager = PromptManager()
        self.llm = LLMService()

    def _chat(self, prompt_name: str, **kwargs) -> str:
        """
        加载 Prompt、渲染模板并调用 LLM。
        """

        system_prompt = self.prompt_manager.get_prompt("system")

        user_prompt = self.prompt_manager.render_prompt(
            prompt_name,
            **kwargs,
        )

        result = self.llm.chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        return result.content