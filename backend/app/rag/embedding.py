"""
Embedding 封装 — 用通义千问 text-embedding-v3 做向量化。

为什么用千问的 API 而不是本地 bge 模型？
- 不用下载数百 MB 模型（绕开 HuggingFace 国内下载源问题）
- OpenAI 兼容接口，直接复用项目已有的 OpenAI SDK
- text-embedding-v3 中文效果好（阿里专门优化）

为什么 text_type 参数很重要？
- RAG 是非对称检索：query 和 document 语义不同
- text_type="query" 编码查询，text_type="document" 编码文档
- 两者用不同的编码方式，检索效果更好
"""

from openai import OpenAI
from backend.app.core.config import settings
from backend.app.core.logger import logger


class EmbeddingService:
    """千问 embedding 封装"""

    def __init__(self):
        self._client = None
        # embedding 缓存：避免相同文本反复调 API（尤其知识库构建时 title 重复、查询重复）
        # key = (text, text_type)，value = 向量 list。内存缓存，重启清空。
        self._cache: dict[tuple[str, str], list[float]] = {}
        self._cache_hits = 0
        self._cache_misses = 0

    @property
    def available(self) -> bool:
        """是否配置了 DashScope Key"""
        return bool(settings.DASHSCOPE_API_KEY)

    @property
    def cache_hits(self) -> int:
        """缓存命中次数（评测/调优时可观察缓存收益）"""
        return self._cache_hits

    @property
    def cache_misses(self) -> int:
        """缓存未命中次数（未命中会实际调 API）"""
        return self._cache_misses

    @property
    def client(self) -> OpenAI:
        """懒加载 OpenAI 客户端（指向 DashScope 兼容接口）"""
        if self._client is None:
            self._client = OpenAI(
                api_key=settings.DASHSCOPE_API_KEY,
                base_url=settings.DASHSCOPE_BASE_URL,
            )
        return self._client

    def embed(self, text: str, text_type: str = "document") -> list[float] | None:
        """
        把一段文本转成向量。

        :param text: 要向量化的文本
        :param text_type: "query"（查询）或 "document"（文档）
        :return: 向量（list[float]），失败返回 None
        """
        if not self.available or not text or not text.strip():
            return None

        cache_key = (text, text_type)
        if cache_key in self._cache:
            self._cache_hits += 1
            return self._cache[cache_key]

        self._cache_misses += 1
        try:
            resp = self.client.embeddings.create(
                model=settings.EMBEDDING_MODEL,
                input=text,
                dimensions=settings.EMBEDDING_DIMENSIONS,
                encoding_format="float",
                extra_body={"text_type": text_type},
            )
            vec = resp.data[0].embedding
            self._cache[cache_key] = vec
            return vec
        except Exception as e:
            logger.warning(f"embedding 失败：{e}")
            return None

    def embed_query(self, query: str) -> list[float] | None:
        """编码查询（text_type=query）"""
        return self.embed(query, text_type="query")

    def embed_document(self, document: str) -> list[float] | None:
        """编码文档（text_type=document）"""
        return self.embed(document, text_type="document")
