"""
知识库初始化脚本 — 把面试知识点文档向量化存入向量库。

用法（backend 目录，配置好 DASHSCOPE_API_KEY 后）：
    python -m backend.app.rag.build_knowledge_base

知识内容在 knowledge_docs.py 里维护，扩充内容只改那个文件。
"""

from backend.app.rag.rag_pipeline import RAGPipeline
from backend.app.rag.knowledge_docs import KNOWLEDGE_DOCS
from backend.app.core.logger import logger


def build() -> int:
    """构建知识库，返回成功索引的 chunk 数（增量：未变化文档跳过）"""
    pipeline = RAGPipeline()
    if not pipeline.available:
        logger.error("未配置 DASHSCOPE_API_KEY，无法构建知识库")
        return 0

    # 把 title 拼进正文一起向量化，让 title 也参与检索；
    # 再按分块策略切块（当前知识库每篇是独立知识点，整篇成块）
    items = []
    for d in KNOWLEDGE_DOCS:
        text = f"{d['title']}\n{d['text']}"
        items.extend(pipeline._chunk_items(d["id"], text))

    success = pipeline.index_batch(items)
    logger.info(f"知识库构建完成：{success}/{len(items)} 个 chunk 索引成功")
    return success


if __name__ == "__main__":
    build()
