"""
TokenBudget 测试（断言式）

TokenBudget 是纯函数逻辑（截断、token 估算），最适合单测。
覆盖 fit_history（近期优先截断）和 fit_text（保留尾部）。
"""

from backend.app.memory.token_budget import TokenBudget


def test_fit_history_keeps_recent():
    """近期优先：token 超限时保留最近的、丢弃最早的"""
    budget = TokenBudget(total=1000)
    budget.reserve(0)
    messages = [
        {"role": "user", "content": "第" + str(i) + "条消息，内容很长" * 20}
        for i in range(10)
    ]
    result = budget.fit_history(messages)
    # 最近的（第 9 条）应该被保留
    assert "第9条消息" in result
    # 最早的（第 0 条）应该被丢弃
    assert "第0条消息" not in result


def test_fit_history_empty():
    budget = TokenBudget()
    assert budget.fit_history([]) == "（无对话历史）"


def test_fit_text_keep_tail():
    """fit_text 默认保留尾部（近期优先）"""
    budget = TokenBudget(total=100)
    budget.reserve(0)
    # 构造一个明显超限的文本：头部是 A，尾部是近期内容
    text = "A" * 1000 + "近期重要内容"
    result = budget.fit_text(text)
    # 保留尾部，所以"近期重要内容"应该在结果里
    assert "近期重要内容" in result


def test_fit_text_keep_head():
    """fit_text(keep_tail=False) 保留头部"""
    budget = TokenBudget(total=100)
    budget.reserve(0)
    text = "开头重要内容" + "B" * 1000
    result = budget.fit_text(text, keep_tail=False)
    assert "开头重要内容" in result


def test_estimate_tokens_chinese_and_english():
    """token 估算：中文 1 字符 ≈ 1.5，英文 1 词 ≈ 1.3"""
    # "你好世界你好世界你好世界" = 12 个中文字符 × 1.5 = 18
    zh = TokenBudget._estimate_tokens("你好世界你好世界你好世界")
    assert zh == 18
    # "hello world" = 2 词(2*1.3) + 1 空格(1.0) = 3.6 → int = 3
    en = TokenBudget._estimate_tokens("hello world")
    assert en == 3


def test_remaining_after_reserve():
    budget = TokenBudget(total=8000)
    budget.reserve(2500)
    assert budget.remaining() == 5500
