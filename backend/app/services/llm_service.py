from openai import OpenAI

from backend.app.core.config import settings
from backend.app.core.exceptions import LLMServiceError, LLMResponseError
from backend.app.core.logger import logger
import time
from backend.app.schemas.chat import ChatResult




class LLMService:

    def __init__(self):
        """LLM service for chat completion."""
        self.client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
        )

        self.model = settings.MODEL_NAME
        # 累计 token 统计（整个 Agent 生命周期）
        self._total_prompt_tokens = 0
        self._total_completion_tokens = 0

    @property
    def total_tokens(self) -> int:
        return self._total_prompt_tokens + self._total_completion_tokens

    def reset_token_counters(self) -> None:
        """清零 token 计数器（Agent 在每轮执行开始时调用）"""
        self._total_prompt_tokens = 0
        self._total_completion_tokens = 0

    def chat(
            self,
            system_prompt: str,
            user_prompt: str,
    ) -> ChatResult:
        last_error = None
        for attempt in range(1, settings.LLM_MAX_RETRIES + 1):
            try:
                start = time.perf_counter()
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    timeout=settings.LLM_TIMEOUT,  # ← 防无限挂起
                )
                elapsed = round(time.perf_counter() - start, 3)
                usage = response.usage
                self._total_prompt_tokens += (usage.prompt_tokens if usage else 0)
                self._total_completion_tokens += (usage.completion_tokens if usage else 0)
                return ChatResult(
                    content=response.choices[0].message.content,
                    model=response.model,
                    elapsed=elapsed,
                    prompt_tokens=usage.prompt_tokens if usage else 0,
                    completion_tokens=usage.completion_tokens if usage else 0,
                    total_tokens=usage.total_tokens if usage else 0,
                )
            except Exception as e:
                last_error = e
                logger.warning(
                    "LLM 调用失败（第 %d/%d 次）：%s",
                    attempt, settings.LLM_MAX_RETRIES, e,
                )
                if attempt < settings.LLM_MAX_RETRIES:
                    time.sleep(2 ** attempt)

        logger.error("LLM 调用重试 %d 次仍失败", settings.LLM_MAX_RETRIES)
        raise LLMServiceError(
            f"LLM 调用失败（重试 {settings.LLM_MAX_RETRIES} 次后仍失败）",
            original_error=last_error,
        )

    def chat_stream(self, system_prompt: str, user_prompt: str):
        """
        流式调用 LLM，逐 token 返回。

        返回一个 generator，每次 yield 一个 token 字符串。
        与 chat() 的区别：
        - chat() 等待完整响应，返回 ChatResult（含 token 统计）
        - chat_stream() 边生成边返回，不做 token 统计（流结束才能统计）

        设计决策：流式不做自动重试。
        因为重试意味着从头开始——前端已经渲染了前半段文本，
        重试会导致文本突然消失又重来，体验比直接报错更差。
        """
        logger.info("LLMService: 开始流式调用")
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                stream=True,
                timeout=settings.LLM_TIMEOUT,
            )
        except Exception as e:
            raise LLMServiceError("流式 LLM 调用失败", original_error=e)
        for chunk in response:
            try:
                delta = chunk.choices[0].delta
                if delta.content is not None:
                    yield delta.content
            except (AttributeError, IndexError, TypeError):
                # 某些 chunk 可能不包含 content（如首尾特殊消息），
                # 这些情况不应中断整个流
                continue
        logger.info("LLMService: 流式调用结束")
