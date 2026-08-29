"""
RAG 管线 — 统一封装 embedding + 向量存储 + 混合检索。

用法：
    pipeline = RAGPipeline()
    pipeline.index("doc_1", "这是文档内容")
    results = pipeline.search("查询内容")
"""

from pathlib import Path
from backend.app.rag.embedding import EmbeddingService
from backend.app.rag.vector_store import VectorStore
from backend.app.rag.hybrid_searcher import HybridSearcher
from backend.app.rag.chunker import TextChunker, chunk_document
from backend.app.rag.reranker import Reranker, KeywordReranker
from backend.app.core.logger import logger

# 持久化路径：backend/data/rag_store.json
# 注意：必须和 database.py 的 DATA_DIR 一致（backend/data/），
# 这样才会被 docker-compose 的 sqlite_data 卷持久化，避免 --build 后数据丢失。
# rag_pipeline.py 在 backend/app/rag/ 下，parents[2] = backend/
STORE_PATH = Path(__file__).resolve().parents[2] / "data" / "rag_store.json"


class RAGPipeline:
    """RAG 检索管线：分块 → embedding → 存储 → 混合检索 → 重排。

    三种检索模式（供评测对比，也是面试的叙事线）：
    - "vector"：纯向量检索（bi-encoder 余弦相似度）
    - "hybrid"：向量 + BM25 + RRF 混合检索（默认）
    - "hybrid+rerank"：混合检索召回 top_n 后再精排
    """

    def __init__(
        self,
        chunker: TextChunker | None = None,
        reranker: Reranker | None = None,
        rerank_top_n: int = 20,
    ):
        self.embedding = EmbeddingService()
        self.vector_store = VectorStore(str(STORE_PATH))
        self.searcher = HybridSearcher(self.vector_store)
        self.chunker = chunker or TextChunker()
        self.reranker = reranker or KeywordReranker()
        self.rerank_top_n = rerank_top_n

    @property
    def available(self) -> bool:
        """RAG 是否可用（需要配置 DashScope Key）"""
        return self.embedding.available

    def _chunk_items(self, doc_id: str, text: str) -> list[tuple[str, str]]:
        """把一篇文档切成 [(chunk_id, chunk_text)]，切块粒度由 chunker 决定"""
        return chunk_document(doc_id, text, self.chunker)

    def index(self, doc_id: str, text: str) -> bool:
        """索引一篇文档（按分块策略切块后向量化）"""
        if not self.available:
            logger.warning("RAG 不可用（未配置 DASHSCOPE_API_KEY）")
            return False
        items = self._chunk_items(doc_id, text)
        return self.index_batch(items) == len(items)

    def index_batch(self, items: list[tuple[str, str]]) -> int:
        """批量索引 [(doc_id, text), ...]，返回成功数量。

        增量更新：跳过「已存在且内容未变」的文档，避免重复调 embedding。
        """
        if not self.available:
            return 0
        success = 0
        indexed = []
        existing_texts = {
            doc_id: self.vector_store.get_text(doc_id)
            for doc_id, _ in items
        }
        for doc_id, text in items:
            # 内容未变则跳过（增量更新的核心判断）
            if existing_texts.get(doc_id) == text:
                logger.info(f"RAG 增量更新：跳过未变化的文档 {doc_id}")
                continue
            vector = self.embedding.embed_document(text)
            if vector is not None:
                indexed.append((doc_id, text, vector))
                success += 1
        if indexed:
            self.vector_store.add_batch(indexed)
            self.searcher._rebuild_bm25()
        return success

    def search(self, query: str, top_k: int = 5, mode: str = "hybrid") -> list[dict]:
        """检索入口，返回 [{"id", "text", "score"}]。

        :param mode: "vector" / "hybrid" / "hybrid+rerank"
        """
        if not self.available:
            return []
        query_vector = self.embedding.embed_query(query)
        if query_vector is None:
            return []

        if mode == "vector":
            # 纯向量：直接取向量检索 top_k
            return self.vector_store.search(query_vector, top_k=top_k)

        # 混合检索：向量 + BM25 + RRF，召回 top_n 候选
        candidates = self.searcher.search(query, query_vector, top_k=self.rerank_top_n)

        if mode == "hybrid":
            return candidates[:top_k]

        # 混合 + 重排：召回 top_n 后精排，再取 top_k
        reranked = self.reranker.rerank(query, candidates, top_k=top_k)
        return reranked

    def top1_vector_similarity(self, query: str) -> float | None:
        """
        取 top-1 的向量余弦相似度（0~1），用于拒答阈值判断。

        为什么单独走向量检索、不取 hybrid 的 RRF 分数？
        RRF 是排名融合分数，量纲不定、不可跨查询比较；向量余弦相似度
        才是有语义含义的 0~1 相似度，可以设一个全局阈值区分「命中」和「知识库外」。

        :return: top-1 的余弦相似度；知识库为空或查询向量失败返回 None
        """
        if not self.available:
            return None
        query_vector = self.embedding.embed_query(query)
        if query_vector is None:
            return None
        results = self.vector_store.search(query_vector, top_k=1)
        if not results:
            return None
        return float(results[0]["score"])


# 全局单例（懒加载）
_pipeline: RAGPipeline | None = None


def get_rag_pipeline() -> RAGPipeline:
    """获取全局 RAG 管线单例"""
    global _pipeline
    if _pipeline is None:
        _pipeline = RAGPipeline()
    return _pipeline
