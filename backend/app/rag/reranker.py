"""
重排器（Reranker）—— 召回之后的精排

为什么召回之后还要重排？
召回阶段（向量检索 + BM25）追求「快」和「全」：向量检索是双塔模型
（query 和 doc 分别编码成向量再算相似度，可以离线建索引、在线快速算），
BM25 是词频统计。它们各自都有盲区——向量对精确词不敏感，BM25 不懂同义词。

重排阶段追求「准」：把召回的前 top_n 个候选，用更精细的模型重新打分排序，
把真正相关的顶到前面。cross-encoder（交叉编码器）把 query 和 doc 一起送进
Transformer，注意力机制让两者充分交互，精度远高于双塔，但慢——所以只对
召回后的少量候选（如 top-20）重排，这是「粗排 + 精排」的标准两阶段架构。

本模块的定位（诚实说清边界）：
- 定义了 Reranker 抽象接口，业务代码只依赖接口，实现可替换。
- 内置一个零依赖的 KeywordReranker（关键词精排）——它不算真正的 cross-encoder，
  但能在「近义干扰」场景里，靠精确词匹配把正确文档顶上来，配合评测验证
  「重排这一层有增益」。这比什么都不做强，且能讲清「重排解决什么问题」。
- 预留了 CrossEncoderReranker 的接入点（bge-reranker / Jina 等），
  当前知识库 23 篇规模不需要，规模增长或对精度要求更高时再上。

两阶段检索架构（面试话术）：
  粗排（recall，快而全）    精排（precision，慢而准）
  bi-encoder + BM25 + RRF  →  cross-encoder 对 top-20 重排
  每篇文档离线编码一次          只对候选做，候选少所以扛得住
"""

from abc import ABC, abstractmethod
import re
from typing import Sequence


class Reranker(ABC):
    """重排器抽象接口：输入候选文档列表，输出按相关性重排后的列表。"""

    @abstractmethod
    def rerank(self, query: str, candidates: list[dict], top_k: int | None = None) -> list[dict]:
        """
        :param query: 用户查询
        :param candidates: [{"id", "text", "score"}...] 粗排结果
        :param top_k: 重排后返回前多少，None 表示全部
        :return: 重排后的候选列表（保持 id/text 字段，score 为精排分）
        """
        raise NotImplementedError


class KeywordReranker(Reranker):
    """
    零依赖关键词精排。

    思路：对每个候选，统计「查询词（token）在候选文本里出现的次数」，
    作为精排分叠加到粗排分上。这样：
    - 精确关键词题：正确文档命中更多 query token，被顶上去。
    - 语义题：token 命中未必有用，但粗排分（向量相似度）仍然主导，不伤语义题。

    注意：这是「重排层存在价值」的证明性实现，不是工业级 cross-encoder。
    面试时要能说清：真正的 reranker 用 cross-encoder，两者原理差异是
    「双塔分别编码 vs 交叉编码全交互」。
    """

    def __init__(self, weight: float = 0.5):
        """
        :param weight: 关键词精排分在最终分里的权重（0~1），
                       越大越偏向关键词匹配，越小越偏向原粗排分。
        """
        self.weight = max(0.0, min(1.0, weight))

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        # 与 BM25 一致：中文按字、英文按词
        return re.findall(r"[a-zA-Z]+|[一-鿿]", (text or "").lower())

    def _keyword_score(self, query: str, text: str) -> float:
        q_tokens = set(self._tokenize(query))
        if not q_tokens:
            return 0.0
        doc_tokens = self._tokenize(text)
        hits = sum(1 for t in q_tokens if t in doc_tokens)
        return hits / len(q_tokens)

    def rerank(self, query: str, candidates: list[dict], top_k: int | None = None) -> list[dict]:
        scored = []
        for c in candidates:
            base = float(c.get("score", 0.0))
            kw = self._keyword_score(query, c.get("text", ""))
            # 组合分：粗排分归一化贡献 (1-weight)，关键词贡献 weight
            final = (1 - self.weight) * base + self.weight * kw
            scored.append({"id": c.get("id"), "text": c.get("text", ""), "score": round(final, 6)})
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k] if top_k is not None else scored


# 可选：接入真实 cross-encoder 时实现这个类（当前未启用）
class CrossEncoderReranker(Reranker):
    """
    cross-encoder 精排接入点（预留，当前规模不需要）。

    用法示例（需 pip install sentence-transformers + 本地/API 模型）：
        from sentence_transformers import CrossEncoder
        model = CrossEncoder("BAAI/bge-reranker-base")
        reranker = CrossEncoderReranker(model)
    """

    def __init__(self, model):
        self.model = model

    def rerank(self, query: str, candidates: list[dict], top_k: int | None = None) -> list[dict]:
        pairs = [(query, c.get("text", "")) for c in candidates]
        scores = self.model.predict(pairs)
        scored = [
            {"id": c.get("id"), "text": c.get("text", ""), "score": round(float(s), 6)}
            for c, s in zip(candidates, scores)
        ]
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k] if top_k is not None else scored
