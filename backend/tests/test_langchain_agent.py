"""
LangChain Agent 纯函数单测（断言式，不依赖 LLM API）

重点测重写后的两个纯函数：
1. _extract_final_answer —— 从 messages 里稳健提取最终回答
2. _chunk_text —— 固定字符数切片

这两个是旧版翻车的地方（字符串匹配 + 多层 break），现在抽象成纯函数，
用 mock 消息对象验证边界行为，锁死回归。
"""

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from backend.app.langchain_agent.agent import LangChainAgent


# ============================================================
#  _extract_final_answer
# ============================================================

def test_extract_final_answer_normal():
    """正常流程：最后一条 AI 消息是最终回答"""
    msgs = [
        HumanMessage(content="帮我分析简历"),
        AIMessage(content="", tool_calls=[{"name": "analyze_resume", "args": {}, "id": "1"}]),
        ToolMessage(content="简历分析结果...", tool_call_id="1"),
        AIMessage(content="这是最终的回答"),
    ]
    assert LangChainAgent._extract_final_answer(msgs) == "这是最终的回答"


def test_extract_final_answer_skips_tool_and_human():
    """只调了工具、没给最终回答时：不把 ToolMessage 或用户提问当回答"""
    msgs = [
        HumanMessage(content="帮我分析简历"),
        AIMessage(content="", tool_calls=[{"name": "analyze_resume", "args": {}, "id": "1"}]),
        ToolMessage(content="简历分析结果...", tool_call_id="1"),
    ]
    # 最后一条是 ToolMessage，应跳过，找不到 AIMessage 回答 → None
    assert LangChainAgent._extract_final_answer(msgs) is None


def test_extract_final_answer_skips_empty_ai():
    """中间态 AIMessage（空 content + tool_calls）应被跳过"""
    msgs = [
        HumanMessage(content="hi"),
        AIMessage(content="", tool_calls=[{"name": "analyze_resume", "args": {}, "id": "1"}]),
    ]
    assert LangChainAgent._extract_final_answer(msgs) is None


def test_extract_final_answer_empty_messages():
    """空消息列表返回 None"""
    assert LangChainAgent._extract_final_answer([]) is None


# ============================================================
#  _chunk_text
# ============================================================

def test_chunk_text_basic():
    """按固定字符数切片，且拼接后等于原文（不丢字）"""
    text = "这是一段测试文本用于验证切片逻辑是否正确工作"
    chunks = LangChainAgent._chunk_text(text, size=10)
    assert "".join(chunks) == text
    assert all(len(c) <= 10 for c in chunks)


def test_chunk_text_empty():
    assert LangChainAgent._chunk_text("") == []


def test_chunk_text_exact_multiple():
    """长度刚好是 size 整数倍时，最后一块也正确"""
    text = "abcdefghij"  # 10 字符
    chunks = LangChainAgent._chunk_text(text, size=5)
    assert chunks == ["abcde", "fghij"]
