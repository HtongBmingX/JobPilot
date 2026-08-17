"""
LangChain 版 Agent 执行器（修复版）

修复了什么？
原来的 run_stream() 用 asyncio.new_event_loop() + threading 在 FastAPI 的
同步端点中跑异步生成器，导致连接断开、事件循环冲突等问题。

修复方案：
1. 同步 run() 保持不动——它一直在正常工作
2. 流式改成分阶段处理：
   a. 用 agent_executor.invoke() 同步执行 Agent（得到完整的 Tool 调用结果）
   b. 从结果中提取业务分析结果
   c. 模仿手写版的 Synthesize 环节：用 LLM stream 做流式终答
3. 这样既保留了流式体验（用户看到逐 token 输出），又避免了 astream_events 的 async/sync 阻抗不匹配
"""

from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import SystemMessage, HumanMessage
from backend.app.langchain_agent.llm import create_llm, chat_sync, chat_stream
from backend.app.langchain_agent.tools import ALL_TOOLS
from backend.app.prompts.prompt_manager import PromptManager
from backend.app.core.logger import logger


class LangChainAgent:
    """
    LangChain 版 JobPilot Agent。

    和手写 JobPilotAgent 的接口完全一致：
    - run(query) → str（同步）
    - run_stream(query) → generator（流式，逐 token yield）
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

    def run(self, query: str, thread_id: str = "default") -> str:
        """
        同步执行 Agent。
        """
        logger.info(f"LangChain Agent 同步执行 | thread_id={thread_id}")

        config = {"configurable": {"thread_id": thread_id}}
        messages = [HumanMessage(content=query)]

        try:
            result = self.agent_executor.invoke(
                {"messages": messages},
                config=config,
            )
            # 提取最后一条 AI 消息
            final_messages = result.get("messages", [])
            for msg in reversed(final_messages):
                if hasattr(msg, 'content') and msg.content:
                    return msg.content

            return "Agent 未生成回复"
        except Exception as e:
            logger.error(f"LangChain Agent 执行失败：{e}", exc_info=True)
            return f"执行失败：{e}"

    def run_stream(self, query: str, thread_id: str = "default"):
        """
        流式执行 Agent，逐 token yield。

        修复方案：
        1. 同步执行 Agent（invoke），收集 Tool 调用结果
        2. 从结果中提取各 Tool 返回的分析文本
        3. 用 Synthesize prompt + LLM stream 做流式终答

        为什么这样改？
        - 异步生成器在同步 FastAPI 端点中很难适配
        - 手写版的 Synthesize 逻辑被验证过——基于 Tool 结果做流式终答
        - 这样做保留了流式体验，且不会崩溃
        """
        logger.info(f"LangChain Agent 流式执行 (fixed) | thread_id={thread_id}")

        config = {"configurable": {"thread_id": thread_id}}
        messages = [HumanMessage(content=query)]

        try:
            # Step 1: 同步执行 Agent（收集所有结果）
            result = self.agent_executor.invoke(
                {"messages": messages},
                config=config,
            )

            # Step 2: 提取 Tool 调用的分析结果
            resume_analysis = ""
            jd_analysis = ""
            match_result = ""

            result_messages = result.get("messages", [])
            for msg in result_messages:
                if not hasattr(msg, 'content') or not msg.content:
                    continue

                content = msg.content

                # Tool 返回的消息通常有特定的前缀（如 "## 简历分析"）
                if "resume" in msg.__class__.__name__.lower() or "简历" in content:
                    resume_analysis = content
                elif "jd" in msg.__class__.__name__.lower() or "岗位" in content:
                    jd_analysis = content
                elif "match" in msg.__class__.__name__.lower() or "匹配" in content:
                    match_result = content

            # 如果没提取到，直接取最后一条 AI 消息
            while not resume_analysis and not jd_analysis and not match_result:
                for msg in reversed(result_messages):
                    if hasattr(msg, 'content') and msg.content:
                        final = msg.content[:200]
                        if "简历" in final:
                            resume_analysis = msg.content
                        elif "岗位" in final or "JD" in final:
                            jd_analysis = msg.content
                        elif "匹配" in final:
                            match_result = msg.content
                        else:
                            # 直接流式推送最后一条消息
                            for chunk in chat_stream("", ""):
                                pass
                            # 如果是纯文本回复（不需要 Synthesize），直接用最后一条消息
                            msg_obj = None
                            for m2 in reversed(result_messages):
                                if hasattr(m2, 'content') and m2.content:
                                    msg_obj = m2
                                    break

                            if msg_obj:
                                temp_llm = create_llm()
                                resp = temp_llm.stream(
                                    [HumanMessage(content="请把以下内容原样输出：\n" + str(msg_obj.content))]
                                )
                                for chunk in resp:
                                    if chunk.content:
                                        yield {"event": "synthesize_chunk", "data": {"text": chunk.content}}
                                break
                        break
                break

            # Step 3: 流式 Synthesize
            if resume_analysis or jd_analysis or match_result:
                synthesize_prompt = self.prompt_manager.render_prompt(
                    "synthesize",
                    query=query,
                    resume_analysis=resume_analysis or "（未提供）",
                    jd_analysis=jd_analysis or "（未提供）",
                    match_result=match_result or "（未提供）",
                    conversation_history="（无对话历史）",
                )

                for token in chat_stream(
                    system_prompt=self.system_prompt,
                    user_prompt=synthesize_prompt,
                ):
                    yield {"event": "synthesize_chunk", "data": {"text": token}}

            yield {"event": "done", "data": {}}

        except Exception as e:
            logger.error(f"LangChain Agent 流式执行失败：{e}", exc_info=True)
            yield {"event": "error", "data": {"message": str(e)}}
