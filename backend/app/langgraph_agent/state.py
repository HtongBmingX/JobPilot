"""AgentState — LangGraph StateGraph 的状态定义

每个节点收到这个 state，修改后返回更新值。
LangGraph 自动合并（用 Annotated reducer 处理 messages 的增量追加）。
"""

from typing import TypedDict, Annotated, Optional
from langgraph.graph.message import add_messages


class AgentState(TypedDict, total=False):
    # ---- 输入 ----
    query: str
    resume: str
    jd: str
    session_id: str

    # ---- 对话历史（add_messages 自动把新消息追加到已有列表） ----
    messages: Annotated[list, add_messages]

    # ---- 业务记忆（各 Tool 节点执行后写入） ----
    resume_analysis: Optional[str]
    jd_analysis: Optional[str]
    match_result: Optional[str]

    # ---- 控制流 ----
    next_action: str           # router 节点填充：resume/jd/match/chat/interview/synthesize/finish
    step_count: int

    # ---- 最终输出 ----
    final_response: Optional[str]
