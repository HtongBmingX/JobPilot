"""
文档分块器（Chunking）

为什么需要分块？
向量检索的检索单位是「块」（chunk）而不是「整篇文档」。块太大，
检索粒度粗、命中后塞进 prompt 的内容冗长；块太小，语义碎片化、丢失上下文。

当前知识库的实际情况：23 篇文档，每篇 500~1500 字，是「一个独立知识点」——
每篇本来就围绕一个主题（定义 + 要点 + 追问 + 易错点），天然就是一个 chunk。
所以默认策略是「整篇成块」。

但这个类存在的原因（面试要讲清楚）：
1. 把「分块」抽象成可替换策略——当前数据用整篇，未来文档变长/跨主题时，
   切块策略（滑动窗口 + 重叠）已经准备好，改配置即可，不动检索代码。
2. 明确什么时候「必须切」：
   - 文档长（几千字、跨多个主题）→ 整篇向量会稀释语义，检索漂移
   - 检索粒度要求细（用户问一个子问题，希望命中某个段落而非整篇）
   - 有 token 限制（一个 chunk 塞不进 prompt 预算）

分块的两个核心参数（面试必问）：
- chunk_size：块大小。太小语义破碎，太大粒度粗。常见 256~1024 token。
- chunk_overlap：块间重叠。让跨块边界的信息不丢失，常见 10%~20% chunk_size。

本实现的分词是「按字符近似」——中文按字、英文按词估算，与 TokenBudget 一致。
对知识库这种短文本够用，不引入重依赖。
"""

import re
from typing import Iterator


class TextChunker:
    """可配置的文本分块器。"""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        """
        :param chunk_size: 每块的最大字符数（近似 token）
        :param chunk_overlap: 相邻块的重叠字符数
        """
        self.chunk_size = max(1, chunk_size)
        self.chunk_overlap = max(0, min(chunk_overlap, self.chunk_size - 1))

    def chunk(self, text: str) -> list[str]:
        """把一段文本切成若干块。

        文本长度 <= chunk_size 时，整篇作为一块返回（当前知识库的默认路径）。
        """
        text = (text or "").strip()
        if not text:
            return []
        if len(text) <= self.chunk_size:
            return [text]

        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            chunks.append(text[start:end])
            if end >= len(text):
                break
            # 下一块从「end - overlap」开始，制造重叠
            start = end - self.chunk_overlap
        return chunks


def chunk_document(doc_id: str, text: str, chunker: TextChunker | None = None) -> list[tuple[str, str]]:
    """
    把一篇文档切成「块」，返回 [(chunk_id, chunk_text), ...]。

    chunk_id 约定为 f"{doc_id}#0"、f"{doc_id}#1" ...，
    评测时把 chunk_id 前缀归一化回 doc_id 即可判定命中（见 eval_runner）。

    :param doc_id: 文档 id
    :param text: 文档全文
    :param chunker: 分块器，默认 TextChunker()
    """
    chunker = chunker or TextChunker()
    chunks = chunker.chunk(text)
    # 单块时保留原始 doc_id（与旧版整篇索引的 id 向后兼容，避免重建时产生孤儿数据）；
    # 多块时才追加 #0/#1 后缀区分
    if len(chunks) == 1:
        return [(doc_id, chunks[0])]
    return [(f"{doc_id}#{i}", c) for i, c in enumerate(chunks)]


def normalize_chunk_id(chunk_id: str) -> str:
    """把 'doc_id#3' 归一到 'doc_id'，用于评测命中判定。"""
    return str(chunk_id).split("#", 1)[0]
