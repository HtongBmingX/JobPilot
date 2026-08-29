"""
LLMService 单测（断言式，mock 隔离，不打真实 API）

覆盖：
- chat() 返回 ChatResult，content 正确
- chat() 累计 token 计数（prompt + completion）
- reset_token_counters 清零
- chat_stream 逐 token yield

重试逻辑在 test_llm_retry.py 里单独测，这里不重复。
"""

from unittest.mock import patch, MagicMock
from backend.app.services.llm_service import LLMService
from backend.app.schemas.chat import ChatResult


def _mock_response(content="OK", prompt=10, completion=5):
    resp = MagicMock()
    resp.choices = [MagicMock()]
    resp.choices[0].message.content = content
    resp.model = "deepseek-chat"
    resp.usage = MagicMock()
    resp.usage.prompt_tokens = prompt
    resp.usage.completion_tokens = completion
    resp.usage.total_tokens = prompt + completion
    return resp


def test_chat_returns_chat_result():
    svc = LLMService()
    with patch.object(svc.client.chat.completions, "create", return_value=_mock_response()):
        result = svc.chat(system_prompt="s", user_prompt="u")
    assert isinstance(result, ChatResult)
    assert result.content == "OK"
    assert result.prompt_tokens == 10
    assert result.completion_tokens == 5


def test_chat_accumulates_tokens():
    svc = LLMService()
    svc.reset_token_counters()
    with patch.object(svc.client.chat.completions, "create", return_value=_mock_response(prompt=10, completion=5)):
        svc.chat(system_prompt="s", user_prompt="u")
    assert svc.total_tokens == 15


def test_reset_token_counters():
    svc = LLMService()
    # 先累计，再清零
    with patch.object(svc.client.chat.completions, "create", return_value=_mock_response(prompt=3, completion=2)):
        svc.chat(system_prompt="s", user_prompt="u")
    assert svc.total_tokens == 5
    svc.reset_token_counters()
    assert svc.total_tokens == 0


def test_chat_stream_yields_tokens():
    svc = LLMService()
    chunks = []
    for i in range(3):
        c = MagicMock()
        c.choices = [MagicMock()]
        c.choices[0].delta = MagicMock()
        c.choices[0].delta.content = f"token{i}"
        chunks.append(c)
    with patch.object(svc.client.chat.completions, "create", return_value=iter(chunks)):
        out = list(svc.chat_stream(system_prompt="s", user_prompt="u"))
    assert out == ["token0", "token1", "token2"]
