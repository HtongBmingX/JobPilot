"""
Answer Relevancy（回答相关性）评测指标

定义：回答是否紧扣用户的问题，有没有答非所问。

算法：
1. 用 LLM 从回答反推可能的问题（generated questions）
2. 计算每个 generated question 与原始 question 的余弦相似度
3. Relevancy = 平均相似度

关键洞察：如果回答真正在回答问题，那么从回答反推出来的问题
应该与原始问题高度相似。如果回答跑偏了（比如问匹配度却一直在分析简历），
反推出来的问题就不像原始问题。

为什么不用 DeepSeek embedding 而用本地模型？
embedding 只是做余弦相似度，不需要生成能力，本地 bge-small 速度更快且零费用。
"""

from backend.app.services.llm_service import LLMService
import hashlib
import math


class AnswerRelevancyMetric:
    def __init__(self, llm: LLMService = None, embed_fn=None):
        self.llm = llm or LLMService()
        self._embed = embed_fn  # 外部注入的 embedding 函数

    def _generate_questions(self, answer: str) -> list[str]:
        """从回答反推可能的用户问题"""
        prompt = f"""请从以下求职分析回答中，反推 3 个可能的用户提问问题。
每行一个，用 - 开头。只输出问题本身。

回答：
{answer}

反推的问题："""

        result = self.llm.chat(
            system_prompt="你是一个擅长逆向推理的助手。只输出问题列表。",
            user_prompt=prompt,
        )
        questions = []
        for line in result.content.split("\n"):
            stripped = line.strip()
            if stripped.startswith("- "):
                questions.append(stripped[2:])
            elif stripped.startswith("-"):
                questions.append(stripped[1:])
        return questions[:3]  # 最多 3 个

    def _simple_embed(self, text: str) -> list[float]:
        """简单的字符级 n-gram embedding（不依赖任何模型）"""
        text = text.lower()
        vec = [0.0] * 128
        # 2-gram hashing (使用 hashlib 保证确定性，Python hash() 受 PYTHONHASHSEED 影响不唯一)
        for i in range(len(text) - 1):
            h = int(hashlib.sha256(text[i:i + 2].encode("utf-8")).hexdigest(), 16) % 128
            vec[h] += 1.0
        # normalize
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec

    def _cosine_sim(self, a: list[float], b: list[float]) -> float:
        return sum(x * y for x, y in zip(a, b))

    def score(self, question: str, answer: str) -> dict:
        """计算 relevancy 分数"""
        embed_fn = self._embed or self._simple_embed
        generated_qs = self._generate_questions(answer)
        if not generated_qs:
            return {"score": 0.0, "generated_questions": [], "similarities": []}

        orig_emb = embed_fn(question)
        similarities = []
        for gq in generated_qs:
            gq_emb = embed_fn(gq)
            sim = self._cosine_sim(orig_emb, gq_emb)
            similarities.append({"question": gq, "similarity": round(sim, 4)})

        avg_sim = sum(s["similarity"] for s in similarities) / len(similarities)
        return {
            "score": round(avg_sim, 4),
            "generated_questions": generated_qs,
            "similarities": similarities,
        }
