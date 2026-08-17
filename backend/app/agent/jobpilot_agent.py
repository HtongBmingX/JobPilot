from backend.app.agent.planner import Planner
from backend.app.tools.registry import ToolRegistry
from backend.app.schemas.plan import Plan
from backend.app.memory.memory_manager import MemoryManager
from backend.app.memory.session_memory import SessionMemory
from backend.app.memory.token_budget import TokenBudget
from backend.app.memory.conversation_summarizer import ConversationSummarizer
from backend.app.agent.agent_state import AgentStateMachine
from backend.app.core.logger import logger
from backend.app.prompts.prompt_manager import PromptManager
from backend.app.services.llm_service import LLMService
import json



class JobPilotAgent:
    """
    JobPilot 的 Agent 主体。

    采用 ReAct（Reason + Act）模式：
        思考(Planner) → 行动(Tool) → 观察(结果存入 Memory) → 再思考 ...
    直到 Planner 返回 finish，或达到最大步数。
    """

    # 触发摘要压缩的消息数量阈值（超过此数量，早期对话被压缩）
    SUMMARY_THRESHOLD = 8
    # 保留最近 N 条消息的原文（不压缩）
    KEEP_RECENT = 4

    def __init__(
        self,
        registry: ToolRegistry,
        memory_manager: MemoryManager | None = None,
    ):
        self.planner = Planner()
        self.registry = registry
        # MemoryManager 缺省内部自建；传入则支持跨请求复用同一会话
        self.memory_manager = memory_manager or MemoryManager()

        self.prompt_manager = PromptManager()
        self.llm = LLMService()
        self.summarizer = ConversationSummarizer(self.llm)

    def execute(
        self,
        query: str,
        session_id: str | None = None,
        max_steps: int = 6,
        user_profile: str | None = None,
        resume: str | None = None,
        jd: str | None = None,
    ) -> str:
        # 每次执行开始时重置 Token 计数（这轮对话从 0 开始）
        self.llm.reset_token_counters()

        if session_id:
            memory = self.memory_manager.create_session(session_id)
        else:
            memory = SessionMemory()

        # 画像存入 memory（本次执行期间使用，不持久化——每次从数据库读取最新画像）
        memory.user_profile = user_profile

        # 简历/JD 原文单独存 memory，不拼进 query（避免污染意图判断）
        # 关键：检测到新简历/JD 时，清除旧的分析结果，让状态机重新分析
        if resume and resume != memory.resume:
            memory.resume = resume
            memory.resume_analysis = None  # 新简历 → 旧分析作废
        if jd and jd != memory.jd:
            memory.jd = jd
            memory.jd_analysis = None      # 新 JD → 旧分析作废

        memory.add_user_message(query)
        history_text = self._build_conversation_history(memory)

        # 前置短路：如果当前只是追问（Memory 里已有业务分析结果），
        # 直接走 Synthesize，不浪费 LLM 调用在 Planner 决策上。
        if self._is_followup(memory, query):
            logger.info("[Agent] 检测到追问，跳过 Planner 直接 Synthesize")
            answer = self._synthesize(memory, query, history_text)
            memory.add_assistant_message(answer)
            if session_id:
                self.memory_manager.save_session(session_id, memory)
            return answer

        for step in range(1, max_steps + 1):
            logger.info(f"[Agent] 第 {step} 步：规划中...")

            # ========================================================
            # Phase 2 状态机代码化：代码决定「当前允许哪些 action」，
            # LLM 只负责从 allowed 中做选择。这是确定性和灵活性的
            # 分界线——规则由代码保证，语义由 LLM 判断。
            # ========================================================

            # Step 1: 代码状态机计算允许的动作
            allowed = AgentStateMachine.compute_allowed_actions(memory, query)
            logger.info(f"[Agent] 代码状态机允许的动作: {allowed}")

            # Step 2: 如果唯一允许 chat，直接走 ChatNode，不调 LLM Planner
            if allowed == ["chat"]:
                logger.info("[Agent] 代码状态机决定 chat，走自然对话")
                self._clear_interview_if_requested(memory, query)
                answer = self._chat(memory, query, history_text)
                memory.add_assistant_message(answer)
                if session_id:
                    self.memory_manager.save_session(session_id, memory)
                return answer

            # Step 3: 如果唯一允许 finish，直接走 finish，不调 LLM
            if allowed == ["finish"]:
                logger.info("[Agent] 代码状态机决定 finish，跳过 Planner")
                answer = self._synthesize(memory, query, history_text)
                memory.add_assistant_message(answer)
                if session_id:
                    self.memory_manager.save_session(session_id, memory)
                return answer

            # Step 3: 如果只有一个非 finish/非chat 选项，代码直接决定 action
            if len(allowed) == 1 and allowed[0] not in ("finish", "chat"):
                auto_action = allowed[0]
                logger.info(f"[Agent] 代码状态机直接决定 action={auto_action}，跳过 LLM 决策")

                # 提取对应的原文（从 memory 取，query 是纯用户输入）
                action_input = {}
                if auto_action == "resume":
                    action_input["resume"] = memory.resume or query
                elif auto_action == "jd":
                    action_input["jd"] = memory.jd or query
                elif auto_action == "match":
                    action_input = {}  # 系统自动注入 resume_analysis + jd_analysis
                elif auto_action == "search":
                    action_input["query"] = query  # 用用户的原始问题检索
                elif auto_action == "interview":
                    action_input["mode"] = memory.interview_mode or "mixed"
                    action_input["resume_analysis"] = memory.resume_analysis
                    action_input["jd_analysis"] = memory.jd_analysis
                    action_input["round_number"] = memory.interview_round + 1
                    action_input["conversation_history"] = history_text

                plan = Plan(
                    thought=f"代码状态机：唯一合法动作={auto_action}，已自动决策",
                    action=auto_action,
                    action_input=action_input,
                )
            else:
                # Step 4: 多个选项 或 多个选项中含 finish，
                #   此时需要 LLM 来做语义判断——
                #   例如用户同时提供了简历和 JD，LLM 应判断
                #   "先分析简历，再分析 JD，最后做匹配"
                plan = self.planner.think(
                    query=query,
                    tools=self.registry.build_prompt(),
                    memory=self._format_memory(memory),
                    conversation_history=history_text,
                )

            logger.info(f"[Agent] 决策：action={plan.action} | {plan.thought}")

            # 校验 Planner 返回的 action 是否在状态机允许的范围内
            # LLM 可能不听话，返回 allowed 之外的 action（如未分析就 match）
            if plan.action not in allowed and plan.action != "finish":
                logger.warning(
                    f"[Agent] Planner 返回了不允许的 action={plan.action}（allowed={allowed}），"
                    f"降级为直接 synthesize"
                )
                answer = self._synthesize(memory, query, history_text)
                memory.add_assistant_message(answer)
                if session_id:
                    self.memory_manager.save_session(session_id, memory)
                return answer

            if plan.action == "finish":
                logger.info("[Agent] 生成最终总结（基于 Memory 真实结果）")
                answer = self._synthesize(memory, query, history_text)
                memory.add_assistant_message(answer)
                if session_id:
                    self.memory_manager.save_session(session_id, memory)
                return answer

            if not self.registry.exists(plan.action):
                logger.warning(f"[Agent] 未知 Tool：{plan.action}，跳过本轮")
                continue

            tool = self.registry.get(plan.action)
            kwargs = dict(plan.action_input)

            if plan.action == "match":
                kwargs.setdefault("resume_analysis", memory.resume_analysis)
                kwargs.setdefault("jd_analysis", memory.jd_analysis)

            # resume/jd 工具补上 memory 里的原文（Planner 的 action_input 可能缺）
            if plan.action == "resume":
                kwargs.setdefault("resume", memory.resume or query)
            if plan.action == "jd":
                kwargs.setdefault("jd", memory.jd or query)

            # search 工具补上查询内容
            if plan.action == "search":
                kwargs.setdefault("query", query)

            # interview 也需要注入分析结果 + 轮数 + 对话历史
            if plan.action == "interview":
                kwargs.setdefault("resume_analysis", memory.resume_analysis)
                kwargs.setdefault("jd_analysis", memory.jd_analysis)
                kwargs.setdefault("mode", memory.interview_mode or "mixed")
                kwargs.setdefault("round_number", memory.interview_round + 1)
                kwargs.setdefault("conversation_history", history_text)

            result = tool.run(**kwargs)

            self._store_result(memory, plan.action, result)

            # 单工具分析完成后直接 synthesize 出报告，避免下一轮走到 chat
            # 条件：刚执行的是 resume/jd（单内容分析）或 search（知识库检索）
            if plan.action in ("resume", "jd"):
                only_single = (memory.resume and not memory.jd) or (memory.jd and not memory.resume)
                if only_single:
                    logger.info("[Agent] 单工具分析完成，直接 synthesize 出报告")
                    answer = self._synthesize(memory, query, history_text)
                    memory.add_assistant_message(answer)
                    if session_id:
                        self.memory_manager.save_session(session_id, memory)
                    return answer
            elif plan.action == "search":
                logger.info("[Agent] 知识库检索完成，直接 synthesize 出报告")
                answer = self._synthesize(memory, query, history_text)
                memory.add_assistant_message(answer)
                if session_id:
                    self.memory_manager.save_session(session_id, memory)
                return answer

        return "已达到最大步数，任务可能未完成，请补充信息后重试。"

    def _store_result(
        self,
        memory: SessionMemory,
        action: str,
        result: str,
    ) -> None:
        """把某一步的执行结果存进会话记忆。"""
        if action == "resume":
            memory.resume_analysis = result
        elif action == "jd":
            memory.jd_analysis = result
        elif action == "match":
            memory.match_result = result
        elif action == "search":
            memory.search_result = result
            # 代码强制提取来源标题（不依赖 LLM）
            import re
            sources = re.findall(r"【KB来源:(.+?)】", result)
            memory.search_sources = list(dict.fromkeys(sources))  # 去重保序
            # 清理结果里的标题标记，只留正文（标题已存 search_sources）
            memory.search_result = re.sub(r"【KB来源:(.+?)】\n?", "", result)
        elif action == "interview":
            # 面试结果不存进 match_result，但更新面试状态：
            # 进入面试模式 + 轮数递增
            memory.interview_mode = memory.interview_mode or "mixed"
            memory.interview_round += 1

    def _clear_interview_if_requested(self, memory: SessionMemory, query: str) -> None:
        """用户喊停面试时，清除面试状态"""
        from backend.app.agent.agent_state import _query_mentions_end_interview
        if _query_mentions_end_interview(query):
            logger.info("[Agent] 用户结束面试，清除面试状态")
            memory.interview_mode = None
            memory.interview_round = 0

    @staticmethod
    def _format_memory(memory: SessionMemory) -> str:
        """把会话记忆中"已完成"的部分整理成给 Planner 看的文本。"""
        done = []
        if memory.resume_analysis:
            done.append("- 简历分析已完成")
        if memory.jd_analysis:
            done.append("- JD 分析已完成")
        if memory.match_result:
            done.append("- 岗位匹配已完成")
        return "\n".join(done) if done else "（尚无已完成步骤）"

    def _synthesize(self, memory: SessionMemory, query: str, conversation_history: str = "") -> str:
        """基于 Memory 中的真实分析结果，生成接地的最终答案。"""
        system_prompt = self.prompt_manager.get_prompt("system")
        user_prompt = self.prompt_manager.render_prompt(
            "synthesize",
            query=query,
            resume_analysis=memory.resume_analysis or "（未提供）",
            jd_analysis=memory.jd_analysis or "（未提供）",
            match_result=memory.match_result or "（未提供）",
            search_result=memory.search_result or "（未检索）",
            conversation_history=conversation_history,
            user_profile=memory.user_profile or "（无）",
        )
        result = self.llm.chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        return self._prepend_sources(result.content, memory)

    def _prepend_sources(self, answer: str, memory: SessionMemory) -> str:
        """代码强制在回答开头加来源标注（不依赖 LLM 听话）"""
        if not memory.search_sources:
            return answer
        sources_line = "、".join(memory.search_sources)
        return f"> 📚 参考来源：{sources_line}\n\n{answer}"

    def _chat(self, memory: SessionMemory, query: str, conversation_history: str = "") -> str:
        """ChatNode：基于已有记忆做自然对话，不调工具，不生产新分析"""
        system_prompt = self.prompt_manager.get_prompt("system")
        user_prompt = self.prompt_manager.render_prompt(
            "chat",
            query=query,
            resume_analysis=memory.resume_analysis or "（未提供）",
            jd_analysis=memory.jd_analysis or "（未提供）",
            match_result=memory.match_result or "（未提供）",
            conversation_history=conversation_history,
            user_profile=memory.user_profile or "（无）",
        )
        result = self.llm.chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        return result.content

    # ============================================================
    #  流式执行（SSE）
    #  设计决策：execute_stream 是 execute 的姐妹方法，不加到同一
    #  个方法里用 flag 区分。原因：
    #    - 同步和异步的控制流差异太大（return vs yield）
    #    - 混在一起会让两个路径都变得难懂
    #    - 各自独立后，未来移除此方法也不会影响同步端点
    # ============================================================

    def execute_stream(self, query: str, session_id: str | None = None, max_steps: int = 6, user_profile: str | None = None, resume: str | None = None, jd: str | None = None):
        # 每次执行开始时重置 Token 计数
        self.llm.reset_token_counters()

        if session_id:
            memory = self.memory_manager.create_session(session_id)
        else:
            memory = SessionMemory()

        # 画像存入 memory（本次执行期间使用）
        memory.user_profile = user_profile

        # 简历/JD 原文单独存 memory，不拼进 query
        # 关键：检测到新简历/JD 时，清除旧的分析结果
        if resume and resume != memory.resume:
            memory.resume = resume
            memory.resume_analysis = None
        if jd and jd != memory.jd:
            memory.jd = jd
            memory.jd_analysis = None

        memory.add_user_message(query)
        history_text = self._build_conversation_history(memory)

        # 前置短路：追问直接 Synthesize
        if self._is_followup(memory, query):
            logger.info("[Agent-Stream] 检测到追问，跳过 Planner 直接 Synthesize")
            accumulate = ""
            for event in self._synthesize_stream(memory, query, history_text):
                if event["event"] == "synthesize_chunk":
                    accumulate += event["data"]["text"]
                yield event
            memory.add_assistant_message(accumulate)
            self.memory_manager.save_session(session_id, memory) if session_id else None
            yield {"event": "done", "data": {}}
            return

        for step in range(1, max_steps + 1):
            logger.info(f"[Agent-Stream] 第 {step} 步：规划中...")

            # Phase 2 代码状态机
            allowed = AgentStateMachine.compute_allowed_actions(memory, query)
            logger.info(f"[Agent-Stream] 代码状态机允许的动作: {allowed}")

            if allowed == ["chat"]:
                logger.info("[Agent-Stream] 代码状态机决定 chat，走自然对话")
                self._clear_interview_if_requested(memory, query)
                accumulate = ""
                for event in self._chat_stream(memory, query, history_text):
                    if event["event"] == "synthesize_chunk":
                        accumulate += event["data"]["text"]
                    yield event
                memory.add_assistant_message(accumulate)
                if session_id:
                    self.memory_manager.save_session(session_id, memory)
                yield {"event": "done", "data": {}}
                return

            if allowed == ["finish"]:
                logger.info("[Agent-Stream] 代码状态机决定 finish，跳过 Planner")
                accumulate = ""
                for event in self._synthesize_stream(memory, query, history_text):
                    if event["event"] == "synthesize_chunk":
                        accumulate += event["data"]["text"]
                    yield event
                memory.add_assistant_message(accumulate)
                if session_id:
                    self.memory_manager.save_session(session_id, memory)
                yield {"event": "done", "data": {}}
                return

            if len(allowed) == 1 and allowed[0] not in ("finish", "chat"):
                auto_action = allowed[0]
                logger.info(f"[Agent-Stream] 代码状态机直接决定 action={auto_action}")
                action_input = {}
                if auto_action == "resume":
                    action_input["resume"] = memory.resume or query
                elif auto_action == "jd":
                    action_input["jd"] = memory.jd or query
                elif auto_action == "match":
                    action_input = {}
                elif auto_action == "search":
                    action_input["query"] = query
                elif auto_action == "interview":
                    action_input["mode"] = memory.interview_mode or "mixed"
                    action_input["resume_analysis"] = memory.resume_analysis
                    action_input["jd_analysis"] = memory.jd_analysis
                    action_input["round_number"] = memory.interview_round + 1
                    action_input["conversation_history"] = history_text

                plan = Plan(
                    thought=f"代码状态机：唯一合法动作={auto_action}，已自动决策",
                    action=auto_action,
                    action_input=action_input,
                )
            else:
                plan = self.planner.think(
                    query=query,
                    tools=self.registry.build_prompt(),
                    memory=self._format_memory(memory),
                    conversation_history=history_text,
                )
            logger.info(f"[Agent-Stream] 决策：action={plan.action} | {plan.thought}")

            # 校验 Planner 返回的 action 是否在状态机允许的范围内
            if plan.action not in allowed and plan.action != "finish":
                logger.warning(
                    f"[Agent-Stream] Planner 返回了不允许的 action={plan.action}（allowed={allowed}），"
                    f"降级为直接 synthesize"
                )
                accumulate = ""
                for event in self._synthesize_stream(memory, query, history_text):
                    if event["event"] == "synthesize_chunk":
                        accumulate += event["data"]["text"]
                    yield event
                memory.add_assistant_message(accumulate)
                if session_id:
                    self.memory_manager.save_session(session_id, memory)
                yield {"event": "done", "data": {}}
                return

            if plan.action == "finish":
                logger.info("[Agent-Stream] 进入 synthesize 流式阶段")
                # 先发一个合成开始信号，让前端知道要开始逐字渲染了
                accumulate = ""
                for event in self._synthesize_stream(memory, query, history_text):
                    if event["event"] == "synthesize_chunk":
                        accumulate += event["data"]["text"]
                    yield event
                # 记录完整回复
                memory.add_assistant_message(accumulate)
                # ================================================
                # Phase 3：每次 Agent 执行完，把 Memory 持久化
                # ================================================
                self.memory_manager.save_session(session_id, memory) if session_id else None
                yield {"event": "done", "data": {}}
                return

            if not self.registry.exists(plan.action):
                logger.warning(f"[Agent-Stream] 未知 Tool：{plan.action}，跳过本轮")
                continue

            # 通知前端：开始执行某个步骤
            yield {
                "event": "step_start",
                "data": {"step": plan.action, "thought": plan.thought},
            }

            tool = self.registry.get(plan.action)
            kwargs = dict(plan.action_input)

            if plan.action == "match":
                kwargs.setdefault("resume_analysis", memory.resume_analysis)
                kwargs.setdefault("jd_analysis", memory.jd_analysis)

            # resume/jd 工具补上 memory 里的原文
            if plan.action == "resume":
                kwargs.setdefault("resume", memory.resume or query)
            if plan.action == "jd":
                kwargs.setdefault("jd", memory.jd or query)

            # search 工具补上查询内容
            if plan.action == "search":
                kwargs.setdefault("query", query)

            # interview Tool 也需要注入分析结果 + 轮数 + 对话历史
            if plan.action == "interview":
                kwargs.setdefault("resume_analysis", memory.resume_analysis)
                kwargs.setdefault("jd_analysis", memory.jd_analysis)
                kwargs.setdefault("mode", memory.interview_mode or "mixed")
                kwargs.setdefault("round_number", memory.interview_round + 1)
                kwargs.setdefault("conversation_history", history_text)

            result = tool.run(**kwargs)
            self._store_result(memory, plan.action, result)

            # 通知前端：步骤完成
            yield {
                "event": "step_done",
                "data": {"step": plan.action},
            }

            # 单工具分析完成后直接 synthesize 出报告（流式）
            if plan.action in ("resume", "jd"):
                only_single = (memory.resume and not memory.jd) or (memory.jd and not memory.resume)
                if only_single:
                    logger.info("[Agent-Stream] 单工具分析完成，直接 synthesize 出报告")
                    accumulate = ""
                    for event in self._synthesize_stream(memory, query, history_text):
                        if event["event"] == "synthesize_chunk":
                            accumulate += event["data"]["text"]
                        yield event
                    memory.add_assistant_message(accumulate)
                    if session_id:
                        self.memory_manager.save_session(session_id, memory)
                    yield {"event": "done", "data": {}}
                    return
            elif plan.action == "search":
                logger.info("[Agent-Stream] 知识库检索完成，直接 synthesize 出报告")
                accumulate = ""
                for event in self._synthesize_stream(memory, query, history_text):
                    if event["event"] == "synthesize_chunk":
                        accumulate += event["data"]["text"]
                    yield event
                memory.add_assistant_message(accumulate)
                if session_id:
                    self.memory_manager.save_session(session_id, memory)
                yield {"event": "done", "data": {}}
                return

        yield {
            "event": "error",
            "data": {"message": "已达到最大步数，任务可能未完成，请补充信息后重试。"},
        }

    def _synthesize_stream(self, memory: SessionMemory, query: str, conversation_history: str = ""):
        """
        流式 Synthesize：逐 token 发出 synthesize_chunk 事件。

        设计决策：不合并到 _synthesize 里。
        _synthesize 返回 str（同步），这个方法 yield 事件（异步生成器）。
        把两者揉在一起会牺牲各自的清晰度。
        """
        system_prompt = self.prompt_manager.get_prompt("system")
        user_prompt = self.prompt_manager.render_prompt(
            "synthesize",
            query=query,
            resume_analysis=memory.resume_analysis or "（未提供）",
            jd_analysis=memory.jd_analysis or "（未提供）",
            match_result=memory.match_result or "（未提供）",
            search_result=memory.search_result or "（未检索）",
            conversation_history=conversation_history,
            user_profile=memory.user_profile or "（无）",
        )

        # 代码强制在流式开头 yield 来源标注（不依赖 LLM）
        if memory.search_sources:
            sources_line = "、".join(memory.search_sources)
            yield {
                "event": "synthesize_chunk",
                "data": {"text": f"> 📚 参考来源：{sources_line}\n\n"},
            }

        for token in self.llm.chat_stream(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        ):
            yield {
                "event": "synthesize_chunk",
                "data": {"text": token},
            }

    def _chat_stream(self, memory: SessionMemory, query: str, conversation_history: str = ""):
        """流式 ChatNode"""
        system_prompt = self.prompt_manager.get_prompt("system")
        user_prompt = self.prompt_manager.render_prompt(
            "chat",
            query=query,
            resume_analysis=memory.resume_analysis or "（未提供）",
            jd_analysis=memory.jd_analysis or "（未提供）",
            match_result=memory.match_result or "（未提供）",
            conversation_history=conversation_history,
            user_profile=memory.user_profile or "（无）",
        )
        for token in self.llm.chat_stream(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        ):
            yield {
                "event": "synthesize_chunk",
                "data": {"text": token},
            }

    # ============================================================
    #  对话历史构建（Token 预算控制）
    #  设计决策：用一个独立的 TokenBudget 类来管理配额，
    #  而非把截断逻辑直接写在 Agent 里。为什么？
    #    - 可测试：纯函数验证截断结果
    #    - 可替换：以后可以换成"摘要压缩"策略而不动 Agent 代码
    #    - 可配置：上下文窗口大小从 Settings 读取，上线 DeepSeek 更大模型时只需改配置
    # ============================================================

    def _build_conversation_history(self, memory: SessionMemory) -> str:
        """
        从 SessionMemory 的对话历史中，构建一段适配 token 预算的历史文本。

        策略升级（上下文压缩）：
        1. 消息数量 ≤ SUMMARY_THRESHOLD：全部原文，交给 TokenBudget 截断
        2. 消息数量 > SUMMARY_THRESHOLD：
           - 早期消息（超出 KEEP_RECENT 的部分）→ LLM 压缩成摘要（缓存到 memory.summary）
           - 近期消息（KEEP_RECENT 条）→ 保留原文
           - 最终 = 摘要 + 近期原文，交给 TokenBudget 截断
        """
        messages = memory.messages
        if not messages:
            return "（无对话历史）"

        budget = TokenBudget(total=8000)
        budget.reserve(2500)

        # 消息数未超阈值：全部原文，token 级截断
        if len(messages) <= self.SUMMARY_THRESHOLD:
            return budget.fit_history(messages)

        # 消息数超阈值：摘要 + 近期原文
        early_messages = messages[: -self.KEEP_RECENT]
        recent_messages = messages[-self.KEEP_RECENT:]

        # 增量摘要：只摘要"新落入 early 区间"的消息，避免重复压缩已摘要内容
        # summarized_count 记录已摘要到第几条消息
        new_early = early_messages[memory.summarized_count:]
        if new_early:
            new_text = "\n".join(
                f"{m.get('role', '')}: {m.get('content', '')}"
                for m in new_early
            )
            new_summary = self.summarizer.summarize(new_text)
            if new_summary:
                # 与已有摘要合并（旧摘要在前，新摘要追加）
                if memory.summary:
                    memory.summary = f"{memory.summary}\n{new_summary}"
                else:
                    memory.summary = new_summary
                memory.summarized_count = len(early_messages)
                logger.info(
                    "[Agent] 增量摘要：新增 %d 条消息，累计摘要 %d 条",
                    len(new_early), memory.summarized_count,
                )

        summary_text = memory.summary

        # 拼接：摘要 + 近期原文
        parts = []
        if summary_text:
            parts.append(f"【早期对话摘要】\n{summary_text}")
        parts.extend(
            f"{m.get('role', '')}: {m.get('content', '')}"
            for m in recent_messages
        )
        combined = "\n\n".join(parts)

        # token 级截断兜底
        return budget.fit_text(combined)

    def _is_followup(self, memory: SessionMemory, query: str = "") -> bool:
        """
        判断是否为追问：有业务记忆，且当前 query 不涉及新的分析请求。

        修复：之前只要有任何分析结果就当作追问，导致用户上传新简历/JD 后
        无法获得新的分析。现在同时检查 query 是否包含新分析意图。
        """
        from backend.app.agent.agent_state import (
            _query_mentions_resume,
            _query_mentions_jd,
            _query_mentions_interview,
            _query_mentions_end_interview,
            _query_mentions_knowledge,
            _query_mentions_match,
        )

        # 面试进行中：不是追问，交给状态机路由到 interview（继续面试）
        if memory.interview_mode and not _query_mentions_end_interview(query):
            return False

        has_analysis = bool(
            memory.resume_analysis or memory.jd_analysis or memory.match_result
        )
        if not has_analysis:
            return False

        # 如果 query 明确要求新的分析或知识检索，不是追问
        if _query_mentions_resume(query):
            return False
        if _query_mentions_jd(query):
            return False
        if _query_mentions_interview(query):
            return False
        if _query_mentions_knowledge(query):
            return False
        if _query_mentions_match(query):
            return False

        return True
