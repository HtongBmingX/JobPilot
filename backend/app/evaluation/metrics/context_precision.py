"""
Context Precision（上下文精确度）评测指标

定义：检索到的上下文里，真正对回答有用的占多少。

算法（RAGAS 口径）：
1. 对检索到的每条上下文，用 LLM 判断它是否与「参考答案/问题」相关（relevant）
2. Context Precision@k = 相关上下文里排在对的靠前位置的比例（位置加权）
   = Σ(相关上下文的 1/rank) / 相关上下文总数，rank 是该上下文在检索结果中的位置

面试要点：Context Precision 和 Context Recall 是互补的——
Precision 检查检索结果「有没有混入无关内容」（多了无关的会扣分），
Recall 检查「该检索到的有没有都检索到」（漏了关键的会扣分）。

⚠️ 诚实声明：本指标依赖 LLM 判定「上下文是否相关」，有固有噪声
（同一输入两次判定可能不同）。所以它只用于人工参考和定性观察，
不作为可复现的简历数据——这正是项目「检索层用确定性指标、生成层用 LLM 判定」
分层评测的原因。
"""

from backend.app.services.llm_service import LLMService


class ContextPrecisionMetric:
    def __init__(self, llm: LLMService = None):
        self.llm = llm or LLMService()

    def is_relevant(self, question: str, context: str, reference: str = "") -> bool:
        """用 LLM 判断一条上下文是否与问题/参考答案相关"""
        prompt = f"""请判断以下检索到的上下文是否与问题相关（有助于回答这个问题）。
只回答 YES 或 NO。

问题：{question}

参考答案（可能为空）：{reference}

检索到的上下文：
{context[:1000]}

这条上下文与问题相关吗？"""

        result = self.llm.chat(
            system_prompt="你是一个擅长相关性判断的助手。只输出 YES 或 NO。",
            user_prompt=prompt,
        )
        return "YES" in result.content.upper()

    def score(self, question: str, contexts: list[str], reference: str = "") -> dict:
        """
        计算 context precision@k。

        :param question: 用户问题
        :param contexts: 按检索顺序排列的上下文列表
        :param reference: 参考答案（可选，用于相关性判断的依据）
        :return: {"score": 0~1, "relevant_count": n, "total": len(contexts), "details": [...]}
        """
        if not contexts:
            return {"score": 0.0, "relevant_count": 0, "total": 0, "details": []}

        details = []
        relevant_count = 0
        weighted = 0.0
        for i, ctx in enumerate(contexts, start=1):
            rel = self.is_relevant(question, ctx, reference)
            details.append({"rank": i, "relevant": rel, "context": ctx[:80]})
            if rel:
                relevant_count += 1
                weighted += 1.0 / i  # 相关上下文越靠前，贡献越大

        # 位置加权：Σ(1/rank) / 相关上下文总数
        score = weighted / relevant_count if relevant_count else 0.0
        return {
            "score": round(score, 4),
            "relevant_count": relevant_count,
            "total": len(contexts),
            "details": details,
        }
