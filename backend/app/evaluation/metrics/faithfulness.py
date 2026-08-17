"""
Faithfulness（忠实度）评测指标

定义：回答中的每个独立陈述是否都能在来源材料中找到依据。

算法：
1. 用 LLM 将回答拆分为原子陈述（atomic claims）
2. 对每个 claim，用 LLM 检查它是否被来源材料支持
3. Faithfulness = 被支持的 claim 数 / 总 claim 数

面试要点：能讲清楚为什么是 claim extraction + claim verification 两步——
先拆解再验证，而不是直接让 LLM 判"这个回答是否忠实"。
后者是模糊的二进制判断，前者是可量化的逐条证据匹配。
"""

from backend.app.services.llm_service import LLMService


class FaithfulnessMetric:
    def __init__(self, llm: LLMService = None):
        self.llm = llm or LLMService()

    def extract_claims(self, answer: str) -> list[str]:
        """用 LLM 把回答拆成原子陈述"""
        prompt = f"""请把以下求职分析回答拆分为独立的原子陈述，每条一行。
原子陈述 = 一个不可再分的、可以被单独验证真假的陈述句。

回答：
{answer}

原子陈述（每行一条，用 - 开头）："""

        result = self.llm.chat(
            system_prompt="你是一个擅长文本分析的语言助手。只需输出结果，不要解释。",
            user_prompt=prompt,
        )
        claims = []
        for line in result.content.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("- "):
                claims.append(stripped[2:])
            elif stripped.startswith("-"):
                claims.append(stripped[1:])
            elif stripped and claims:
                claims[-1] += " " + stripped
        return claims

    def check_claim(self, claim: str, sources: str) -> bool:
        """
        检查一条陈述是否与来源材料一致。

        关键设计：faithfulness 测的是「编造不存在的事实」，
        不是「分析不够逐字」。所以判定标准是：
        - 陈述中的事实性内容是否与来源一致（或能从来源合理推断）
        - 评价、建议、主观判断不算幻觉（只要它们基于的事实是真实的）

        用三档判定替代原来的 YES/NO 二值，避免把合理的分析误判为幻觉。
        """
        prompt = f"""来源材料：
{sources}

请判断以下陈述中的事实性内容是否与来源材料一致。
判定标准（重要）：
- 如果陈述的事实都能在来源中找到依据，或能从来源合理推断 → YES
- 如果陈述编造了来源中不存在的事实（如虚构的项目、技能、数据）→ NO
- 评价、建议、主观判断（如"技术栈选得好"、"建议补充项目细节"）本身不算编造，
  只要它们提到的事实是真实的，就判 YES

只回答 YES 或 NO。

陈述：{claim}

事实与来源一致？"""

        result = self.llm.chat(
            system_prompt="你是一个擅长事实核查的助手。只输出 YES 或 NO。",
            user_prompt=prompt,
        )
        return "YES" in result.content.upper()

    def score(self, answer: str, sources: str) -> dict:
        """
        计算 faithfulness 分数。

        返回：
            score: 0.0-1.0 的忠实度分数
            supported: 被支持的 claim 数
            total: 总 claim 数
            claims: [(claim, is_supported), ...] 明细
        """
        claims = self.extract_claims(answer)
        if not claims:
            return {"score": 1.0, "supported": 0, "total": 0, "claims": []}

        details = []
        supported_count = 0
        for claim in claims:
            is_supported = self.check_claim(claim, sources)
            details.append({"claim": claim, "supported": is_supported})
            if is_supported:
                supported_count += 1

        return {
            "score": supported_count / len(claims) if claims else 1.0,
            "supported": supported_count,
            "total": len(claims),
            "claims": details,
        }
