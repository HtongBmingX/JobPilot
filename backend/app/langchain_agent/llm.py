"""
LangChain 版 LLM 包装器

为什么需要这个文件？
LangChain 的 ChatOpenAI 原生支持 OpenAI 兼容 API（如 DeepSeek）。
用它来替代手写的 LLMService.chat() 和 chat_stream()。

迁移映射：
  手写 LLMService.chat()       → langchain_llm.invoke()
  手写 LLMService.chat_stream() → langchain_llm.stream()

设计决策：不替换 LLMService，而是提供并行版本。
这样 /agent/run 和 /agent/langchain/run 共存，方便对比。

注意：这里只保留 create_llm() 一个工厂函数。Agent 内部直接用
create_react_agent 自带的 invoke/stream 能力，不再包装 chat_sync/chat_stream
两个中间层——它们曾是旧版 run_stream 的 workaround 依赖，已随重写删除。
"""

from langchain_openai import ChatOpenAI
from backend.app.core.config import settings


def create_llm() -> ChatOpenAI:
    """
    创建 LangChain ChatOpenAI 实例（兼容 DeepSeek API）。

    和手写 LLMService 的配置完全一致：
    - api_key 和 base_url 指向 DeepSeek
    - temperature=0 保证输出确定性（适合结构化输出场景）
    - max_tokens 限制输出长度，避免单次调用消耗过多 token
    """
    return ChatOpenAI(
        model=settings.MODEL_NAME,
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL,
        temperature=0,
        max_tokens=4096,
        timeout=settings.LLM_TIMEOUT,
        max_retries=settings.LLM_MAX_RETRIES,
    )
