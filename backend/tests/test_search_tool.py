"""
SearchTool 拒答阈值单测（断言式，mock 隔离，不打真实 API）

覆盖：
1. RAGPipeline.top1_vector_similarity —— 取 top-1 向量相似度（纯逻辑，用 mock embedding）
2. SearchTool 拒答分支 —— 阈值启用 + 相似度低于阈值时返回「无相关内容」
"""

from unittest.mock import patch
from backend.app.rag.rag_pipeline import RAGPipeline
from backend.app.rag.vector_store import VectorStore
from backend.app.rag.hybrid_searcher import HybridSearcher
from backend.app.rag.reranker import KeywordReranker
from backend.app.tools.search_tool import SearchTool


class _FakeEmbedding:
    """返回可控向量的假 embedding：让 doc1 与查询更相似、doc2 不相似。"""
    available = True

    def __init__(self):
        self.query_vec = [1.0, 0.0]
        self.doc_vecs = {
            "doc1": [1.0, 0.1],   # 与 query 余弦相似度高
            "doc2": [0.1, 1.0],   # 与 query 相似度低
        }

    def embed_query(self, query):
        return self.query_vec

    def embed_document(self, document):
        return self.doc_vecs.get(document, [0.0, 0.0])


def _pipeline_with_fake_embedding() -> RAGPipeline:
    p = RAGPipeline.__new__(RAGPipeline)  # 绕过 __init__ 里的真实 EmbeddingService
    p.embedding = _FakeEmbedding()
    p.vector_store = VectorStore()  # 内存模式
    # 文本用「title\n正文」格式（和真实知识库一致，第一行是标题，
    # 这样 SearchTool 才会给检索结果加 【KB来源:标题】 标记）
    p.vector_store.add("doc1", "简历标题\n简历分析内容", [1.0, 0.1])
    p.vector_store.add("doc2", "无关标题\n无关内容", [0.1, 1.0])
    # search() 会用到 searcher / reranker / rerank_top_n，补齐这几个属性
    p.searcher = HybridSearcher(p.vector_store)
    p.reranker = KeywordReranker()
    p.rerank_top_n = 20
    return p


def test_top1_vector_similarity_returns_top1_score():
    p = _pipeline_with_fake_embedding()
    sim = p.top1_vector_similarity("随便什么查询")
    # doc1 与 query [1,0] 的余弦相似度最高，应 > 0.9
    assert sim is not None
    assert sim > 0.9


def test_top1_vector_similarity_empty_store():
    p = _pipeline_with_fake_embedding()
    p.vector_store = VectorStore()  # 空存储
    assert p.top1_vector_similarity("查询") is None


def test_search_tool_rejects_below_threshold():
    """阈值启用、top1 相似度低于阈值 → 返回拒答文案"""
    p = _pipeline_with_fake_embedding()
    # 用负方向的查询向量，让 top1 余弦相似度很低（负值 < 阈值 0.5）
    # doc1=[1,0.1] 和 doc2=[0.1,1] 都在第一象限，query=[-1,0] 与它们都近乎反向
    p.embedding.query_vec = [-1.0, 0.0]
    with patch("backend.app.tools.search_tool.get_rag_pipeline", return_value=p), \
         patch("backend.app.tools.search_tool.settings") as mock_settings:
        mock_settings.RAG_SIMILARITY_THRESHOLD = 0.5
        result = SearchTool().run(query="完全不相关的问题")
    assert "知识库中没有找到相关内容" in result


def test_search_tool_no_threshold_keeps_behavior():
    """阈值关闭（0.0）→ 不拒答，正常返回检索结果"""
    p = _pipeline_with_fake_embedding()
    with patch("backend.app.tools.search_tool.get_rag_pipeline", return_value=p), \
         patch("backend.app.tools.search_tool.settings") as mock_settings:
        mock_settings.RAG_SIMILARITY_THRESHOLD = 0.0
        result = SearchTool().run(query="简历")
    # 阈值关闭时正常走检索，返回内容里有来源标记
    assert "【KB来源" in result


def test_search_tool_missing_query():
    assert "缺少查询内容" in SearchTool().run(query="")
