"""
RAG 评测体系 + 分块器 + 重排器的单元测试（断言式，不依赖任何外部 API）

覆盖：
- metrics：四个指标纯函数的正确性（含边界、负例返回 None）
- chunker：整篇成块、长文本切块 + 重叠、chunk_id 归一化
- reranker：关键词精排能把命中更多 query 词的文档顶上来
- 离线评测流程：用 HashEmbedding 代理，验证 direct/keyword 类能命中、negative 不召回

这些是纯函数/确定性行为，测试稳定、可复现。
"""

from backend.app.rag.eval.metrics import (
    recall_at_k, precision_at_k, mrr, ndcg_at_k, aggregate,
)
from backend.app.rag.chunker import TextChunker, chunk_document, normalize_chunk_id
from backend.app.rag.reranker import KeywordReranker


# ============================================================
#  指标
# ============================================================

def test_recall_at_k():
    assert recall_at_k(["a", "b", "c"], ["a"], 5) == 1.0
    assert recall_at_k(["x", "y"], ["a"], 5) == 0.0
    assert recall_at_k(["a", "b"], ["a", "c"], 5) == 0.5
    # 前 k 个之外的命中不算
    assert recall_at_k(["x", "a"], ["a"], 1) == 0.0
    # 负例（expected 为空）返回 None
    assert recall_at_k(["x"], [], 5) is None


def test_precision_at_k():
    assert precision_at_k(["a", "b"], ["a"], 2) == 0.5
    assert precision_at_k([], ["a"], 5) == 0.0
    assert precision_at_k(["x"], [], 5) is None


def test_mrr():
    assert mrr(["a", "b"], ["a"]) == 1.0
    assert mrr(["x", "a"], ["a"]) == 0.5
    assert mrr(["x", "y"], ["a"]) == 0.0
    assert mrr(["x"], []) is None


def test_ndcg_at_k():
    # 正确文档排第一 = 满分
    assert ndcg_at_k(["a"], ["a"], 5) == 1.0
    # 正确文档排越后，分数越低
    assert ndcg_at_k(["x", "a"], ["a"], 5) < 1.0
    assert ndcg_at_k(["a", "x"], ["a"], 5) > ndcg_at_k(["x", "a"], ["a"], 5)
    assert ndcg_at_k([], [], 5) is None


def test_aggregate_skips_none():
    assert aggregate([1.0, None, 0.0]) == 0.5
    assert aggregate([None, None], default=-1.0) == -1.0


# ============================================================
#  分块器
# ============================================================

def test_chunker_short_text_single_chunk():
    c = TextChunker(chunk_size=100, chunk_overlap=10)
    assert c.chunk("短文本") == ["短文本"]


def test_chunker_long_text_with_overlap():
    c = TextChunker(chunk_size=10, chunk_overlap=4)
    text = "abcdefghijklmnop"  # 16 字符
    chunks = c.chunk(text)
    assert len(chunks) > 1
    # 相邻块有重叠：前一块结尾 == 后一块开头（重叠 4 字符）
    assert chunks[0][-4:] == chunks[1][:4]


def test_chunker_empty():
    c = TextChunker()
    assert c.chunk("") == []
    assert c.chunk("   ") == []


def test_chunk_document_and_normalize():
    c = TextChunker(chunk_size=10, chunk_overlap=4)
    items = chunk_document("doc1", "abcdefghijklmnop", c)
    assert all(cid.startswith("doc1#") for cid, _ in items)
    assert normalize_chunk_id("doc1#0") == "doc1"
    assert normalize_chunk_id("doc1") == "doc1"


# ============================================================
#  重排器
# ============================================================

def test_keyword_reranker_boosts_hit():
    r = KeywordReranker(weight=1.0)  # 只看关键词
    candidates = [
        {"id": "d1", "text": "redis 缓存 穿透 布隆过滤器", "score": 0.1},
        {"id": "d2", "text": "前端 vue 响应式", "score": 0.9},
    ]
    # query 里 redis 布隆过滤器，d1 词命中多，应被顶到第一
    out = r.rerank("redis 布隆过滤器", candidates)
    assert out[0]["id"] == "d1"


def test_keyword_reranker_preserves_semantic_when_no_hit():
    r = KeywordReranker(weight=1.0)
    candidates = [
        {"id": "d1", "text": "缓存穿透", "score": 0.9},
        {"id": "d2", "text": "前端 vue", "score": 0.1},
    ]
    # query 与两篇都无词面重合，纯按原分排序
    out = r.rerank("zzz 无关词", candidates)
    assert out[0]["id"] == "d1"


# ============================================================
#  离线评测流程冒烟测试（用 HashEmbedding 代理）
# ============================================================

def test_offline_eval_smoke():
    from backend.app.rag.eval.runner import build_offline_pipeline, evaluate

    pipeline = build_offline_pipeline()
    hybrid = evaluate(pipeline, "hybrid", top_k=5)

    # 直接命中题 + 精确关键词题：词面代理能召回，recall 应 > 0
    assert hybrid["recall@5"] > 0.0
    # 所有指标都在合法范围
    for name in ("recall@5", "precision@5", "mrr", "ndcg@5"):
        assert 0.0 <= hybrid[name] <= 1.0, name


def test_offline_negative_low_similarity():
    from backend.app.rag.eval.runner import build_offline_pipeline, evaluate

    pipeline = build_offline_pipeline()
    r = evaluate(pipeline, "vector", top_k=5)
    # 负例（天气/绝育/诺贝尔奖）不该召回高相似文档
    assert r["negative_avg_top1_sim"] < 0.5
