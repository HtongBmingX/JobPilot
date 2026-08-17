"""
LangChain 版 LLM 包装器

为什么需要这个文件？
LangChain 的 ChatOpenAI 原生支持 OpenAI 兼容 API（如 DeepSeek）。
我们用它来替代手写的 LLMService.chat() 和 chat_stream()。

迁移映射：
  手写 LLMService.chat()    → langchain_llm.invoke()
  手写 LLMService.chat_stream() → langchain_llm.stream()

关键区别：
  手写版本：
    LLMService.chat(system_prompt="...", user_prompt="...")
    返回 ChatResult(content="...", model="...", elapsed=1.2, tokens={...})

  LangChain 版本：
    llm.invoke([SystemMessage("..."), HumanMessage("...")])
    返回 AIMessage(content="...", response_metadata={"token_usage": {...}})

设计决策：不替换 LLMService，而是提供并行版本。
这样 /agent/run 和 /agent/langchain/run 共存，方便对比。
"""

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from backend.app.core.config import settings
from backend.app.core.logger import logger


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


def chat_sync(system_prompt: str, user_prompt: str) -> str:
    """
    同步调用 LLM（LangChain 版）。

    和手写 LLMService.chat() 的接口完全一致：
    传入 system_prompt 和 user_prompt 两个字符串，返回模型回复的内容字符串。

    区别：
    - 手写版返回 ChatResult 对象（含 content/model/elapsed/token 统计）
    - LangChain 版返回纯字符串（简化，保留核心能力）

    如果你想保留 token 统计，可以用 llm.invoke() 返回的 AIMessage.response_metadata。
    但当前同步端点主要用于测试，不需要完整统计。
    """
    llm = create_llm()
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]
    response = llm.invoke(messages)
    content = response.content if hasattr(response, 'content') else str(response)
    logger.info(f"LangChain LLM 返回成功，长度 {len(content)} 字符")
    return content


def chat_stream(system_prompt: str, user_prompt: str):
    """
    流式调用 LLM（LangChain 版），逐 token yield 字符串。

    和手写 LLMService.chat_stream() 的接口完全一致：
    返回一个 generator，每次 yield 一个 token 字符串。
    """
    llm = create_llm()
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]
    logger.info("LangChain LLM 开始流式调用")
    for chunk in llm.stream(messages):
        if chunk.content:
            yield chunk.content
    logger.info("LangChain LLM 流式调用结束")
