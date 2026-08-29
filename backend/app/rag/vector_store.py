"""
轻量向量存储 — 纯 Python 实现 + JSON 持久化。

为什么不用 Chroma / Faiss 等向量数据库？
- 知识库规模很小（几十篇文档），不需要专用向量数据库的索引能力
- 避免引入重依赖（chromadb 安装重、和 Docker 环境兼容性差）
- 纯 Python 余弦相似度对几百个向量毫秒级，完全够用
- 符合项目"自建"调性——面试时可以讲"我评估了 Chroma，但规模小，自己实现更轻"

设计：文档向量存内存 + JSON 持久化，重启后重新加载。
"""

import json
import math
from pathlib import Path
from backend.app.core.logger import logger


class VectorStore:
    """轻量向量存储：存文档 + 向量，支持余弦相似度检索"""

    def __init__(self, persist_path: str | None = None):
        self._docs: list[dict] = []  # [{"id", "text", "vector"}]
        self._persist_path = Path(persist_path) if persist_path else None
        if self._persist_path and self._persist_path.exists():
            self._load()

    def _load(self) -> None:
        try:
            data = json.loads(self._persist_path.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                logger.warning("VectorStore 持久化文件格式错误（非列表），回退为空")
                self._docs = []
                return
            self._docs = data
            logger.info(f"VectorStore 加载 {len(self._docs)} 篇文档")
        except Exception as e:
            logger.warning(f"VectorStore 加载失败：{e}")
            self._docs = []

    def _save(self) -> None:
        if not self._persist_path:
            return
        try:
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            self._persist_path.write_text(
                json.dumps(self._docs, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as e:
            logger.warning(f"VectorStore 保存失败：{e}")

    def add(self, doc_id: str, text: str, vector: list[float]) -> None:
        """添加文档（幂等：同 id 覆盖）"""
        self._docs = [d for d in self._docs if d["id"] != doc_id]
        self._docs.append({"id": doc_id, "text": text, "vector": vector})
        self._save()

    def add_batch(self, items: list[tuple[str, str, list[float]]]) -> None:
        """批量添加 [(doc_id, text, vector), ...]"""
        ids = {i[0] for i in items}
        self._docs = [d for d in self._docs if d["id"] not in ids]
        for doc_id, text, vector in items:
            self._docs.append({"id": doc_id, "text": text, "vector": vector})
        self._save()

    def search(self, query_vector: list[float], top_k: int = 5) -> list[dict]:
        """
        余弦相似度检索，返回 top_k 个最相关的文档。
        返回 [{"id", "text", "score"}]
        """
        if not self._docs:
            return []
        results = []
        for doc in self._docs:
            sim = self._cosine_similarity(query_vector, doc["vector"])
            results.append({"id": doc["id"], "text": doc["text"], "score": sim})
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def all_docs(self) -> list[dict]:
        """返回所有文档（BM25 用）"""
        return [{"id": d["id"], "text": d["text"]} for d in self._docs]

    def get_text(self, doc_id: str) -> str | None:
        """按 id 取文档文本（增量更新时判断内容是否变化用）"""
        for d in self._docs:
            if d["id"] == doc_id:
                return d["text"]
        return None

    def get_ids(self) -> set[str]:
        """返回当前所有文档 id（增量更新时判断哪些已存在）"""
        return {d["id"] for d in self._docs}

    def __len__(self) -> int:
        return len(self._docs)

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        """余弦相似度（纯 Python，向量维度一致）"""
        if len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)
