"""
SearchTool — RAG 检索工具，让 Agent 能检索知识库。

知识库内容：面试技巧、岗位知识、行业信息等。
当用户问"XX 岗位的面试一般问什么"时，Agent 可以调用这个工具检索知识库。
"""

from backend.app.tools.base_tool import BaseTool
from backend.app.rag.rag_pipeline import get_rag_pipeline
from backend.app.core.logger import logger


class SearchTool(BaseTool):
    name = "search"
    description = "搜索求职知识库（面试技巧、岗位要求、行业知识等），返回相关的知识片段"
    parameters = ["query"]

    def run(self, **kwargs) -> str:
        query = kwargs.get("query", "")
        if not query:
            return "（检索失败：缺少查询内容）"

        pipeline = get_rag_pipeline()
        if not pipeline.available:
            return "（知识库未配置，检索不可用）"

        results = pipeline.search(query, top_k=5)
        if not results:
            return "（知识库中没有找到相关内容）"

        logger.info(f"SearchTool 检索：{query} → {len(results)} 条结果")

        blocks = []
        for i, r in enumerate(results, start=1):
            # r["text"] 第一行是 title（构建时 title 拼在正文前面）
            # 用明确标记包裹标题，便于 Agent 端代码提取来源
            text = r["text"]
            first_newline = text.find("\n")
            if first_newline > 0:
                title = text[:first_newline]
                body = text[first_newline:].lstrip()
                blocks.append(f"【KB来源:{title}】\n{body}")
            else:
                blocks.append(text)
        return "\n\n".join(blocks)
