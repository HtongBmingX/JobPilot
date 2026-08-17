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
    """构建知识库，返回成功索引的文档数"""
    pipeline = RAGPipeline()
    if not pipeline.available:
        logger.error("未配置 DASHSCOPE_API_KEY，无法构建知识库")
        return 0

    # 把 title 拼进文本一起向量化，这样 title 也能参与检索
    items = [
        (d["id"], f"{d['title']}\n{d['text']}")
        for d in KNOWLEDGE_DOCS
    ]
    success = pipeline.index_batch(items)
    logger.info(f"知识库构建完成：{success}/{len(items)} 篇文档索引成功")
    return success


if __name__ == "__main__":
    build()
