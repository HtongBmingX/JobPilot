"""
RAG 检索测试（断言式）

覆盖纯 Python 的向量存储（余弦相似度）和混合检索（BM25 + RRF）。
不依赖外部 API，用固定的小向量验证检索逻辑。
"""

from backend.app.rag.vector_store import VectorStore
from backend.app.rag.hybrid_searcher import HybridSearcher, BM25


def test_cosine_similarity():
    """余弦相似度：相同向量=1，正交=0"""
    assert VectorStore._cosine_similarity([1, 0], [1, 0]) == 1.0
    assert VectorStore._cosine_similarity([1, 0], [0, 1]) == 0.0
    # 长度不同返回 0
    assert VectorStore._cosine_similarity([1, 0], [1, 0, 0]) == 0.0


def test_vector_store_add_and_search():
    """添加文档 + 相似度检索"""
    store = VectorStore()  # 不传 persist_path，内存模式
    store.add("doc1", "后端开发", [1.0, 0.0, 0.0])
    store.add("doc2", "前端开发", [0.0, 1.0, 0.0])
    store.add("doc3", "算法岗位", [0.0, 0.0, 1.0])

    # 查询向量接近 doc1
    results = store.search([1.0, 0.1, 0.0], top_k=1)
    assert results[0]["id"] == "doc1"
    assert results[0]["score"] > 0.9


def test_vector_store_add_idempotent():
    """同 id 重复添加是覆盖，不是追加"""
    store = VectorStore()
    store.add("doc1", "旧内容", [1.0, 0.0])
    store.add("doc1", "新内容", [1.0, 0.0])
    assert len(store) == 1
    assert store.all_docs()[0]["text"] == "新内容"


def test_vector_store_search_empty():
    """空存储返回空结果"""
    store = VectorStore()
    assert store.search([1.0, 0.0]) == []


def test_bm25_search():
    """BM25 关键词检索能命中包含关键词的文档"""
    bm25 = BM25()
    bm25.index(["后端开发工程师", "前端开发工程师", "算法工程师"])
    results = bm25.search("后端", top_k=1)
    assert results[0][0] == 0  # 第一份文档（后端开发）


def test_hybrid_search_combines():
    """混合检索：向量 + BM25 融合后能返回结果"""
    store = VectorStore()
    store.add("doc1", "后端开发", [1.0, 0.0])
    store.add("doc2", "前端开发", [0.0, 1.0])
    searcher = HybridSearcher(store)

    # 查询"后端"，向量也接近 doc1
    results = searcher.search("后端", [1.0, 0.1])
    assert len(results) > 0
    assert results[0]["id"] == "doc1"
