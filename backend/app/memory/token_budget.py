"""
Token 预算控制器 — 管理对话历史在 prompt 中占用的 token 配额。

为什么需要独立的 TokenBudget 类？

1. 可测试：可以用纯数据验证截断逻辑，不依赖 LLM API
2. 可替换：策略（简单截断 vs 摘要压缩 vs 滑动窗口）可以按需切换
3. 单一职责：LLMService 管调用，TokenBudget 管配额，各管各的

Token 预算分配优先级（从高到低）：
  1. system prompt（角色定义）—— 不可压缩
  2. Planner 决策规则 — 不可压缩
  3. 业务记忆（简历/JD/匹配结果）—— 尽可能保留
  4. 对话历史 — 近期优先，超出的截断
"""

from backend.app.core.logger import logger


class TokenBudget:
    """
    管理一个 prompt 的 token 配额。

    用法：
        budget = TokenBudget(total=8000)
        budget.reserve(2000)  # 预留给 system + planner 规则
        history_text = budget.fit_history(messages)  # 截断后剩余部分
    """

    def __init__(self, total: int = 8000):
        """
        :param total: 模型上下文窗口的总 token 数
                      默认 8000（DeepSeek 较小模型的保守值）
        """
        self.total = total
        self.used = 0

    def reserve(self, tokens: int) -> None:
        """预占一段配额，给 system prompt / 业务记忆等固定内容"""
        self.used += tokens

    def remaining(self) -> int:
        """返回剩余可用 token"""
        return max(0, self.total - self.used)

    def fit_history(self, messages: list[dict]) -> str:
        """
        把对话历史格式化为文本，保证不超过剩余配额。

        策略：从最近的对话开始往前取（近期优先），
        直到 token 配额用完或取完所有消息。

        :param messages: [{"role": "user", "content": "..."}, ...]
        :return: 格式化后的对话历史字符串（可直接插入 prompt）
        """
        available = self.remaining()
        if available <= 0 or not messages:
            return "（无对话历史）"

        selected = []
        token_count = 0

        # 从最近的对话开始累积，直到超出配额
        for msg in reversed(messages):
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            line = f"{role}: {content}"
            line_tokens = self._estimate_tokens(line)

            if token_count + line_tokens > available:
                break

            selected.insert(0, line)  # 插入到最前面，保持时间顺序
            token_count += line_tokens

        if not selected:
            logger.warning(
                "TokenBudget: 剩余 %d token 不足以容纳任何历史消息 "
                "（第一条就需要 %d token），将不注入历史",
                available,
                self._estimate_tokens(
                    f"{messages[-1].get('role', '')}: {messages[-1].get('content', '')}"
                ),
            )
            return "（对话历史过长，已省略早期部分）"

        result = "\n".join(selected)
        logger.info(
            "TokenBudget: 从 %d 条历史消息中选取了 %d 条注入 prompt，"
            "预估 %d token",
            len(messages), len(selected), token_count,
        )
        return result

    def fit_text(self, text: str, keep_tail: bool = True) -> str:
        """
        把一段纯文本截断到剩余配额内。

        用于已经拼好的文本（如"摘要 + 近期原文"），按 token 预算做截断。

        :param keep_tail: True 保留尾部（近期内容优先，丢弃头部摘要）；
                          False 保留头部。
        """
        available = self.remaining()
        if available <= 0 or not text:
            return "（无对话历史）"

        est = self._estimate_tokens(text)
        if est <= available:
            return text

        # 超过配额：按比例截断字符（粗略但够用，误差 ±20% 可接受）
        ratio = available / est
        max_chars = int(len(text) * ratio)
        truncated = text[-max_chars:] if keep_tail else text[:max_chars]
        logger.info(
            "TokenBudget: 文本 %d token 超过剩余 %d，按比例截断到 %d 字符",
            est, available, max_chars,
        )
        return truncated + "…"

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """
        粗略估算文本的 token 数。

        为什么不用 tiktoken？
        - tiktoken 的编码器是 OpenAI 专有的，DeepSeek 的 tokenizer 不同
        - 对预算控制来说，±20% 的误差不影响截断决策
        - 中文 1 字符 ≈ 1.5 token，英文 1 单词 ≈ 1.3 token

        :param text: 要估算的文本
        :return: 估算的 token 数
        """
        import re
        # 统计中文字符
        chinese_chars = len(re.findall(r'[一-鿿]', text))
        # 统计英文单词（用空格和标点分隔）
        english_words = len(re.findall(r'[a-zA-Z]+', text))
        # 剩余字符（数字、标点、换行等）按 1:1 估算
        remaining = len(text) - chinese_chars - sum(
            len(w) for w in re.findall(r'[a-zA-Z]+', text)
        )

        return int(chinese_chars * 1.5 + english_words * 1.3 + remaining * 1.0)
