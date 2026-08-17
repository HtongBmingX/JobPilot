"""
RAG 知识库问答评测用例

评测对象：Agent 的 RAG 检索能力——问知识库类问题时，回答是否忠于检索到的知识库文档。

每个用例：
- question: 用户提问（知识库能回答的面试问题）
- sources: 知识库中对应文档的完整内容（faithfulness/recall 的依据）
- expected_key_points: 回答应覆盖的关键点

为什么 sources 用知识库文档原文？
faithfulness 测的是"回答有没有编造知识库之外的内容"，
recall 测的是"知识库关键点有没有被覆盖"。
只有 sources 是明确的知识库内容，这两个指标才有意义。
"""

from backend.app.rag.knowledge_docs import KNOWLEDGE_DOCS

# 建 id -> 文档的映射，方便取 sources
_DOC_MAP = {d["id"]: d for d in KNOWLEDGE_DOCS}


def _doc_text(doc_id: str) -> str:
    """取知识库文档的完整内容（title + text）"""
    doc = _DOC_MAP[doc_id]
    return f"{doc['title']}\n{doc['text']}"


RAG_TEST_CASES = [
    {
        "id": "rag_001",
        "name": "知识库-缓存穿透",
        "question": "后端面试问 Redis 缓存穿透怎么回答？",
        "doc_id": "backend_redis",
        "expected_key_points": ["缓存穿透定义", "布隆过滤器", "缓存空值", "参数校验"],
    },
    {
        "id": "rag_002",
        "name": "知识库-数据库索引",
        "question": "MySQL 索引为什么用 B+ 树？",
        "doc_id": "backend_db_index",
        "expected_key_points": ["B+ 树", "磁盘 IO", "范围查询", "回表"],
    },
    {
        "id": "rag_003",
        "name": "知识库-ReAct 原理",
        "question": "什么是 ReAct 模式？",
        "doc_id": "agent_react",
        "expected_key_points": ["Reason", "Act", "Observe", "循环"],
    },
    {
        "id": "rag_004",
        "name": "知识库-RAG 检索增强",
        "question": "RAG 是什么，为什么要用混合检索？",
        "doc_id": "agent_rag",
        "expected_key_points": ["检索增强", "向量检索", "BM25", "RRF"],
    },
    {
        "id": "rag_005",
        "name": "知识库-Vue 响应式",
        "question": "Vue 的响应式原理是什么？",
        "doc_id": "frontend_vue",
        "expected_key_points": ["Proxy", "Object.defineProperty", "依赖收集"],
    },
]


def get_rag_test_cases() -> list[dict]:
    """返回带 sources 的完整测试用例（sources = 知识库文档原文）"""
    cases = []
    for case in RAG_TEST_CASES:
        doc_id = case["doc_id"]
        cases.append({
            "id": case["id"],
            "name": case["name"],
            "question": case["question"],
            "resume": "",
            "jd": "",
            "sources": _doc_text(doc_id),
            "expected_key_points": case["expected_key_points"],
        })
    return cases
