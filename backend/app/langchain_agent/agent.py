"""
LangChain 版 Agent 执行器（重写版）

设计（和手写版做同输入同输出对比）：
- 手写版：手写 ReAct 循环，工具执行完后显式走 synthesize.md 模板做最终总结。
- LangChain 版：create_react_agent 内部自己完成「工具调用 → 最终回答」，
  最终回答就是 Agent 自己生成的合成答案（LangChain 的 ReAct 内置了 synthesize 能力）。

所以两版的关系是「同一能力的不同实现」：
  手写 = 显式 for 循环 + 显式 synthesize 步骤
  框架 = create_react_agent 封装了同样的循环 + 内置总结
这正是「手写理解本质，框架验证理解」的对比实验。

流式方案（为什么这样设计）：
LangGraph 的 astream_events 是异步的，在 FastAPI 同步端点里有 async/sync
阻抗不匹配（这是旧版踩过的坑）。所以流式端点采用「同步 invoke 一次拿到完整
结果 → 把最终回答分片推送」的稳妥做法：
- 不依赖框架的事件流，不会因为 async/sync 问题崩溃
- 用户体验上仍是渐进渲染（前端逐片 append）
- 不额外调第二次 LLM（避免浪费 token + 引入不确定性）

诚实边界：这不是「逐 token 真流式」，而是「同步执行 + 分片投递」。
面试被问到时如实说：LangChain 流式端点为了避开 astream_events 的
async/sync 阻抗，用同步执行 + 分片投递，手写版的 SSE 才是逐 token 真流式。
"""

from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from backend.app.langchain_agent.llm import create_llm
from backend.app.langchain_agent.tools import ALL_TOOLS
from backend.app.prompts.prompt_manager import PromptManager
from backend.app.core.logger import logger


class LangChainAgent:
    """
    LangChain 版 JobPilot Agent。

    和手写 JobPilotAgent 的接口完全一致：
    - run(query) → str（同步）
    - run_stream(query) → generator（分片投递）
    """

    def __init__(self):
        self.llm = create_llm()
        self.tools = ALL_TOOLS
        self.prompt_manager = PromptManager()
        self.system_prompt = self.prompt_manager.get_prompt("system")

        self.checkpointer = InMemorySaver()

        self.agent_executor = create_react_agent(
            model=self.llm,
            tools=self.tools,
            checkpointer=self.checkpointer,
            prompt=self.system_prompt + "\n\n请使用工具来回答用户的问题。使用 Markdown 格式输出最终分析结果。",
        )

    def _invoke(self, query: str, thread_id: str) -> list:
        """同步执行 Agent，返回最终的 messages 列表。"""
        config = {"configurable": {"thread_id": thread_id}}
        result = self.agent_executor.invoke(
            {"messages": [HumanMessage(content=query)]},
            config=config,
        )
        return result.get("messages", [])

    @staticmethod
    def _extract_final_answer(messages: list) -> str | None:
        """
        从 messages 里提取「最终回答」。

        倒序找第一条「真正的回答」：
        - 跳过 ToolMessage（那是工具返回的结果，不是回答）
        - 跳过 HumanMessage（那是用户输入，不是回答）
        - 跳过内容为空的 AIMessage（那是只带 tool_calls、还没生成文字的中间态）

        这样即使 Agent 中途停住（只调了工具没给最终回答），
        也不会把工具结果或用户提问误当成回答返回。
        """
        for msg in reversed(messages):
            content = getattr(msg, "content", None)
            if not content:
                continue
            if isinstance(msg, (HumanMessage, ToolMessage)):
                continue
            # AIMessage 且 content 非空 → 最终回答
            return content
        return None

    def run(self, query: str, thread_id: str = "default") -> str:
        """同步执行 Agent，返回最终回答字符串。"""
        logger.info(f"LangChain Agent 同步执行 | thread_id={thread_id}")
        try:
            messages = self._invoke(query, thread_id)
            answer = self._extract_final_answer(messages)
            return answer or "Agent 未生成回复"
        except Exception as e:
            logger.error(f"LangChain Agent 执行失败：{e}", exc_info=True)
            return f"执行失败：{e}"

    def run_stream(self, query: str, thread_id: str = "default"):
        """
        流式执行 Agent（同步执行 + 分片投递）。

        yield 事件字典，和手写版 execute_stream 的事件协议一致：
            synthesize_chunk —— 最终回答的一个文本片段
            done —— 完成
            error —— 出错
        """
        logger.info(f"LangChain Agent 流式执行 | thread_id={thread_id}")
        try:
            messages = self._invoke(query, thread_id)
            answer = self._extract_final_answer(messages)
            if not answer:
                yield {"event": "error", "data": {"message": "Agent 未生成回复"}}
                return

            for chunk in self._chunk_text(answer):
                yield {"event": "synthesize_chunk", "data": {"text": chunk}}
            yield {"event": "done", "data": {}}
        except Exception as e:
            logger.error(f"LangChain Agent 流式执行失败：{e}", exc_info=True)
            yield {"event": "error", "data": {"message": str(e)}}

    @staticmethod
    def _chunk_text(text: str, size: int = 120) -> list[str]:
        """
        把完整回答按固定字符数切片。

        为什么按字符切片而不是逐 token：
        - 这里拿到的已经是完整回答，不依赖框架的事件流
        - 分片只是为了让前端渐进渲染，用户体验接近流式
        - 前端每次收到 chunk 都会对整个累积文本重新渲染，所以切片边界不影响最终渲染结果
        """
        return [text[i:i + size] for i in range(0, len(text), size)]
