"""
BM25 关键词检索 + Hybrid Search（向量 + BM25 + RRF 融合）。

为什么需要 BM25 补充向量检索？
- 向量检索擅长语义匹配："后端开发"能匹配"服务端工程师"
- 但向量检索对精确匹配不敏感：搜"Python 3.12"可能返回 Python 3.11 的内容
- BM25 擅长精确关键词匹配，两者互补

为什么用 RRF（Reciprocal Rank Fusion）融合？
- BM25 分数和向量相似度分数尺度不同，直接加权需要调超参
- RRF 基于排名而非分数，天然跨检索器可比
- 公式：score(d) = Σ 1/(k + rank_i(d))，k 通常取 60
"""

import math
import re
from collections import Counter


class BM25:
    """BM25 关键词检索"""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.docs: list[str] = []
        self.doc_len: list[int] = []
        self.avg_len: float = 0.0
        self.doc_freq: Counter = Counter()
        self.doc_count: int = 0

    def index(self, documents: list[str]) -> None:
        """建立索引（documents 是纯文本列表）"""
        self.docs = documents
        self.doc_count = len(documents)
        self.doc_len = [len(self._tokenize(d)) for d in documents]
        self.avg_len = sum(self.doc_len) / max(1, self.doc_count)
        self.doc_freq = Counter()
        for doc in documents:
            terms = set(self._tokenize(doc))
            for t in terms:
                self.doc_freq[t] += 1

    def search(self, query: str, top_k: int = 5) -> list[tuple[int, float]]:
        """返回 [(doc_index, score), ...]，按分数降序"""
        if not self.docs:
            return []
        query_terms = self._tokenize(query)
        scores = []
        for i, doc in enumerate(self.docs):
            score = self._score(doc, query_terms)
            if score > 0:
                scores.append((i, score))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def _score(self, doc: str, query_terms: list[str]) -> float:
        """BM25 打分"""
        doc_terms = self._tokenize(doc)
        doc_term_count = Counter(doc_terms)
        score = 0.0
        for term in query_terms:
            if term not in doc_term_count:
                continue
            df = self.doc_freq.get(term, 0)
            if df == 0:
                continue
            tf = doc_term_count[term]
            idf = math.log((self.doc_count - df + 0.5) / (df + 0.5) + 1)
            denom = tf + self.k1 * (1 - self.b + self.b * (len(doc_terms) / max(1, self.avg_len)))
            score += idf * (tf * (self.k1 + 1)) / denom
        return score

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """分词：中文按字切分，英文按词切分"""
        # 简单分词：中文逐字 + 英文单词
        tokens = re.findall(r'[a-zA-Z]+|[一-鿿]', text.lower())
        return tokens


class HybridSearcher:
    """混合检索：向量 + BM25 + RRF 融合"""

    RRF_K = 60

    def __init__(self, vector_store, rrf_k: int = 60):
        self.vector_store = vector_store
        self.rrf_k = rrf_k  # RRF 的 k 参数，可配置（用于敏感性实验）
        self.bm25 = BM25()
        self._rebuild_bm25()

    def _rebuild_bm25(self) -> None:
        """从向量存储重建 BM25 索引"""
        docs = self.vector_store.all_docs()
        self.bm25.index([d["text"] for d in docs])
        self._doc_id_map = [d["id"] for d in docs]  # index -> doc_id

    def search(self, query: str, query_vector: list[float], top_k: int = 5) -> list[dict]:
        """
        混合检索。

        :param query: 原始查询文本（BM25 用）
        :param query_vector: 查询向量（向量检索用）
        :return: [{"id", "text", "score"}]
        """
        # 1. 向量检索
        vector_results = self.vector_store.search(query_vector, top_k=top_k * 2)
        # 2. BM25 检索
        bm25_results = self.bm25.search(query, top_k=top_k * 2)

        # 3. RRF 融合
        rrf_scores: dict[str, float] = {}
        # 向量结果：rank 从 1 开始
        for rank, r in enumerate(vector_results, start=1):
            rrf_scores[r["id"]] = rrf_scores.get(r["id"], 0) + 1 / (self.rrf_k + rank)
        # BM25 结果
        for rank, (idx, _) in enumerate(bm25_results, start=1):
            doc_id = self._doc_id_map[idx]
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1 / (self.rrf_k + rank)

        # 按 RRF 分数排序
        ranked_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)
        top_ids = ranked_ids[:top_k]

        # 取回文档文本
        doc_map = {d["id"]: d["text"] for d in self.vector_store.all_docs()}
        return [
            {"id": doc_id, "text": doc_map.get(doc_id, ""), "score": round(rrf_scores[doc_id], 4)}
            for doc_id in top_ids
        ]
