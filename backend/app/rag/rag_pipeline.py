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
from backend.app.core.logger import logger

# 持久化路径：backend/data/rag_store.json
# 注意：必须和 database.py 的 DATA_DIR 一致（backend/data/），
# 这样才会被 docker-compose 的 sqlite_data 卷持久化，避免 --build 后数据丢失。
# rag_pipeline.py 在 backend/app/rag/ 下，parents[2] = backend/
STORE_PATH = Path(__file__).resolve().parents[2] / "data" / "rag_store.json"


class RAGPipeline:
    """RAG 检索管线"""

    def __init__(self):
        self.embedding = EmbeddingService()
        self.vector_store = VectorStore(str(STORE_PATH))
        self.searcher = HybridSearcher(self.vector_store)

    @property
    def available(self) -> bool:
        """RAG 是否可用（需要配置 DashScope Key）"""
        return self.embedding.available

    def index(self, doc_id: str, text: str) -> bool:
        """索引一篇文档"""
        if not self.available:
            logger.warning("RAG 不可用（未配置 DASHSCOPE_API_KEY）")
            return False
        vector = self.embedding.embed_document(text)
        if vector is None:
            return False
        self.vector_store.add(doc_id, text, vector)
        self.searcher._rebuild_bm25()
        return True

    def index_batch(self, items: list[tuple[str, str]]) -> int:
        """批量索引 [(doc_id, text), ...]，返回成功数量"""
        if not self.available:
            return 0
        success = 0
        indexed = []
        for doc_id, text in items:
            vector = self.embedding.embed_document(text)
            if vector is not None:
                indexed.append((doc_id, text, vector))
                success += 1
        if indexed:
            self.vector_store.add_batch(indexed)
            self.searcher._rebuild_bm25()
        return success

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """混合检索，返回 [{"id", "text", "score"}]"""
        if not self.available:
            return []
        query_vector = self.embedding.embed_query(query)
        if query_vector is None:
            return []
        return self.searcher.search(query, query_vector, top_k)


# 全局单例（懒加载）
_pipeline: RAGPipeline | None = None


def get_rag_pipeline() -> RAGPipeline:
    """获取全局 RAG 管线单例"""
    global _pipeline
    if _pipeline is None:
        _pipeline = RAGPipeline()
    return _pipeline
