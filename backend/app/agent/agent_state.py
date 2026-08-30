"""
Agent 状态枚举和流转逻辑 — 代码级状态机

为什么从 prompt 状态机迁移到代码状态机？

1. 可靠性：prompt 文本约束本质上是"请求 LLM 遵守规则"，LLM 可能不听话
   - 你之前遇到的 resume 循环卡死就是证据：即使 prompt 说"已完成不可重复执行"，
     LLM 仍然可能选已完成的 action
   - 代码状态机是确定性的——给定状态，输出一定正确

2. Token 成本：每次 Planner 调用都要把"必须按 resume→jd→match 顺序"等
   规则文本注入 prompt——这些规则是固定的，但每次都在消耗 token
   代码状态机让 LLM 只做"语义匹配"（从 query 里提取字段），省掉规则描述 token

3. 面试价值（最重要的）：这是 Agent 架构中"你到底理解多深"的区分点
   - 调包侠：直接用 LangChain AgentExecutor，不知道内部在做什么
   - 手写 prompter：能写 prompt 驱动 ReAct，但遇到 LLM 不听话就得调 prompt
   - 你：先手写理解本质 → 发现问题 → 把状态机下沉到代码 → 未来迁移 LangGraph 能1:1映射

   面试时的完整叙事："我最开始用 prompt 文本做状态机，发现 LLM 不完全遵守规则。
   后来把它迁移到代码中——代码负责'当前允许哪些动作'，LLM 只负责'选哪一个并提取参数'。
   这本质上就是 constrained generation，与 LangGraph 的 conditional_edge 是同一原理。
   所以后来迁移 LangGraph 时，状态机的每个节点和条件分支都能一一对应。"

状态机设计（和 prompt 版本完全对应，但由代码保证）：

   初始 / 空状态
   ├── 用户请求含简历原文 且 简历未分析 → resume
   ├── 用户请求含 JD 原文 且 JD 未分析 → jd
   ├── 简历+JD 都已分析 且 匹配未做 且 请求涉及匹配 → match
   └── 否则 → finish
"""

from enum import Enum
from backend.app.memory.session_memory import SessionMemory


class AgentState(Enum):
    """Agent 执行状态"""
    IDLE = "idle"             # 初始状态，还未执行任何 Tool
    RESUME_ANALYZED = "resume_analyzed"
    JD_ANALYZED = "jd_analyzed"
    MATCH_DONE = "match_done"
    FINISHED = "finished"


class AgentStateMachine:
    """
    确定性状态机——根据 Memory 状态和用户 query，输出下一步该执行的动作。

    这不是 Planner 的替代品，而是 Planner 的前置过滤器：
    - AgentStateMachine 决定「当前允许哪些 action」
    - Planner（LLM）从 allowed 里选一个，并提取 action_input
    """

    @staticmethod
    def compute_allowed_actions(
        memory: SessionMemory,
        query: str,
    ) -> list[str]:
        """
        根据 Memory 和 query 内容，返回当前允许的 action 列表。

        规则（和 planner.md 完全对应）：
        1. 简历未分析 且 query 含简历 → 允许 resume
        2. JD 未分析 且 query 含 JD → 允许 jd
        3. 简历+JD 都已分析 且 匹配未做 → 允许 match
        4. 所有该做的都做完了 → 允许 finish

        如果 query 只有纯聊天/追问，返回 ["finish"]。
        """

        # 语义检测：用户是否提出了需要某个 Tool 的请求
        has_resume_in_query = _query_mentions_resume(query)
        has_jd_in_query = _query_mentions_jd(query)
        wants_interview = _query_mentions_interview(query)
        wants_end_interview = _query_mentions_end_interview(query)
        wants_knowledge = _query_mentions_knowledge(query)
        wants_match = _query_mentions_match(query)

        # Memory 状态：各 Tool 是否已执行
        resume_done = memory.resume_analysis is not None
        jd_done = memory.jd_analysis is not None
        match_done = memory.match_result is not None
        in_interview = memory.interview_mode is not None

        allowed = []

        # 规则 -1：面试进行中 —— 除非用户明确喊停，否则持续路由到 interview
        if in_interview:
            if wants_end_interview:
                return ["chat"]
            return ["interview"]

        # 规则 0.5：知识库检索 —— 问面试题/行业知识等，直接 search
        # 优先于简历/JD 分析（这些是知识性问题，不需要用户简历）
        if wants_knowledge:
            return ["search"]

        # 规则 0：面试模拟优先——明确的面试请求直接路由
        # 但如果 memory 里有简历/JD 原文且尚未分析，先分析再面试（确保面试有据可依）
        # 注意排除"结束面试"（含"面试"二字但语义相反）
        if wants_interview and not wants_end_interview:
            # 基于 memory 里是否有原文判断（而非 query 关键词），
            # 因为用户可能上传了简历但 query 只写"帮我面试"
            if (memory.resume and not resume_done) or (memory.jd and not jd_done):
                if memory.resume and not resume_done:
                    allowed.append("resume")
                if memory.jd and not jd_done:
                    allowed.append("jd")
                if not allowed:
                    allowed = ["interview"]
            else:
                allowed = ["interview"]
            if allowed and allowed != ["interview"]:
                if "interview" not in allowed:
                    allowed.append("interview")
            return allowed

        # 规则 1：简历分析
        if has_resume_in_query and not resume_done:
            allowed.append("resume")

        # 规则 2：JD 分析
        if has_jd_in_query and not jd_done:
            allowed.append("jd")

        # 规则 3：岗位匹配 —— 简历和 JD 都已分析 + 用户明确要匹配
        if resume_done and jd_done and not match_done and wants_match:
            allowed.append("match")

        # 规则 4：如果没有任何待执行的 Tool 但有业务记忆，允许 chat（自然对话）
        if not allowed and not (has_resume_in_query or has_jd_in_query or wants_interview or wants_match):
            allowed = ["chat"]

        # 规则 5：兜底——什么都没命中，直接 chat
        if not allowed:
            allowed = ["chat"]

        return allowed

    @staticmethod
    def determine_action(
        memory: SessionMemory,
        query: str,
    ) -> str | None:
        """
        如果状态明确且只有一个合法选项，直接返回固定的 action（不调 LLM）。

        当有多个合法选项时（例如同时允许 resume 和 jd），返回 None，
        表示需要 LLM 来决定顺序。

        这进一步减少了不必要的 LLM 调用。
        """
        allowed = AgentStateMachine.compute_allowed_actions(memory, query)

        if len(allowed) == 1:
            return allowed[0]

        # 多个选项（如同时允许 resume 和 jd），需要 LLM 判断顺序
        return None


# ============================================================
#  辅助函数：判断 query 是否涉及简历/JD
#  简化版——只做关键词匹配。为什么不用 LLM 判断？
#  - 关键词匹配是确定性的、零 cost、零延迟
#  - 误判代价低：最多多执行一次不必要的 Tool，不会造成严重错误
#  - 如果未来需要更精准的语义判断，可以加一层轻量分类器
# ============================================================

def _query_mentions_resume(query: str) -> bool:
    """判断用户 query 是否涉及简历分析"""
    # 去掉"求职"（太宽泛，几乎所有求职对话都命中）
    keywords = ["简历", "我的背景", "我的经历", "我的技能",
                "resume", "cv", "履历"]
    query_lower = query.lower()
    return any(kw in query_lower for kw in keywords)


def _query_mentions_jd(query: str) -> bool:
    """判断用户 query 是否涉及 JD 分析"""
    # 去掉"角色"（泛指词）；"岗位/职位"保留但注意和知识库路由的优先级
    keywords = ["jd", "岗位", "职位", "招聘", "job description",
                "职位描述", "岗位职责", "任职要求", "工作要求",
                "职位要求", "招聘要求", "用人要求", "jd分析"]
    query_lower = query.lower()
    return any(kw in query_lower for kw in keywords)


def _query_mentions_interview(query: str) -> bool:
    """判断用户 query 是否涉及面试模拟"""
    keywords = ["面试", "模拟面试", "mock interview", "interview",
                "面试官", "面我", "考我", "问我问题", "帮我面试"]
    query_lower = query.lower()
    return any(kw in query_lower for kw in keywords)


def _query_mentions_match(query: str) -> bool:
    """判断用户 query 是否涉及岗位匹配"""
    keywords = ["匹配", "match", "契合", "匹配度", "匹配吗",
                "适不适合", "合适吗", "符不符合", "差距", "帮我对比"]
    query_lower = query.lower()
    return any(kw in query_lower for kw in keywords)


def _query_mentions_end_interview(query: str) -> bool:
    """判断用户 query 是否在请求结束面试"""
    keywords = ["结束面试", "停止面试", "退出面试", "不面试了",
                "面试结束", "结束吧", "不面了", "stop interview"]
    query_lower = query.lower()
    return any(kw in query_lower for kw in keywords)


def _query_mentions_knowledge(query: str) -> bool:
    """
    判断用户 query 是否在问知识库类问题。

    覆盖两类：
    1. 面试准备类（"面试题""怎么准备""怎么回答"）
    2. 技术概念类（"XX 是什么""XX 为什么""XX 原理""XX 怎么实现"）

    技术概念类是知识库的核心场景——用户问"MySQL 索引为什么用 B+ 树"，
    应该走 search 检索知识库，而不是 chat 让 LLM 自由发挥。
    """
    keywords = [
        # 面试准备类
        "面试题", "面试问题", "面试一般问", "面试会问", "面试考",
        "常见问题", "考点", "高频", "八股",
        "怎么准备", "如何准备", "怎么回答", "如何回答",
        "需要学什么", "需要会什么", "行情", "薪资",
        # 技术概念类
        "是什么", "什么是", "为什么", "原理", "怎么实现", "如何实现",
        "区别", "优缺点", "作用", "机制", "流程",
    ]
    query_lower = query.lower()
    return any(kw in query_lower for kw in keywords)


def _query_mentions_external(query: str) -> bool:
    """
    判断用户 query 是否在请求「外部实时信息」（需要 MCP 外部工具，而非本地 RAG）。

    覆盖：
    1. 公司/开源项目信息（"XX 公司的技术栈""XX 的开源项目""面试官的 repo"）
    2. 实时/时效性信息（"最新""最近""现在"）

    设计意图：和 _query_mentions_knowledge 形成「本地知识库 vs 外部工具」的分层——
    知识库能答的走 search（快、零成本、可溯源），知识库答不了、需要实时或外部
    数据源的走 MCP 外部工具（GitHub 等）。这是 RAG + Web/外部工具的混合检索权衡。
    """
    keywords = [
        # 公司/开源项目信息
        "开源项目", "github", "repo", "仓库", "技术栈", "公司用了",
        "公司的项目", "面试官的项目", "这个项目",
        # 实时/时效性
        "最新", "最近", "现在", "今年的",
    ]
    query_lower = query.lower()
    return any(kw in query_lower for kw in keywords)
