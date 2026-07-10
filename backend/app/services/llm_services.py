from http.client import responses

from openai import OpenAI

from backend.app.core.config import settings


class LLMService:

    def __init__(self):
        """LLM service for chat completion."""
        self.client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
        )

        self.model = settings.MODEL_NAME

    def chat(
            self,
            system_prompt: str,
            user_prompt: str,
    ) -> str:  # Call the LLM with system and user prompts.The caller only provides business semantics instead of constructing the OpenAI messages format directly.
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": user_prompt,
                    }
                ]
            )

            return response.choices[0].message.content

        except Exception as e:
            print(f"[LLMService] API call failed: {e}")
        raise  # 保留原始异常栈，用raise会重新抛出异常，错误信息不直观
