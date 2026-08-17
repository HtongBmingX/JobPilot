from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class SessionMemory:
    """
    保存一个用户会话(Session)中的业务数据与对话历史。

    业务记忆（resume_analysis 等）和对话记忆（messages）分开管理：
    - 业务记忆是「事实」——Agent 通过 Tool 调用获得的分析结果
    - 对话记忆是「上下文」——用户和 Agent 之间的交互历史

    为什么用 field(default_factory=list) 而不是 = []？
    Python 的 dataclass 不允许直接用可变对象作为默认值
    （所有实例会共享同一个 list），default_factory 保证每个实例
    独立创建自己的空列表。
    """

    # 原始输入
    resume: str | None = None
    jd: str | None = None

    # AI 分析结果（业务记忆）
    resume_analysis: str | None = None
    jd_analysis: str | None = None

    # AI 匹配结果
    match_result: str | None = None

    # 知识库检索结果（RAG search 工具的输出）
    search_result: str | None = None
    # 知识库来源标题列表（代码从检索结果提取，用于强制来源标注）
    search_sources: list[str] = field(default_factory=list)

    # 面试模拟状态（多轮面试）
    # interview_mode: 当前面试模式（technical/behavioral/mixed），None 表示未在面试中
    # interview_round: 已完成的面试轮数（第 N 轮提问后递增）
    interview_mode: str | None = None
    interview_round: int = 0

    # 用户画像（跨会话长期记忆，本次执行期间注入，不随 session 持久化）
    user_profile: str | None = None

    # 早期对话摘要（上下文压缩的产物，持久化——避免每次重新压缩）
    summary: str | None = None
    # 已摘要到的消息数量（用于增量摘要：新消息落入早期区间时只摘要新增部分）
    summarized_count: int = 0

    # 对话历史（对话记忆）
    # 格式：[{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
    messages: list[dict] = field(default_factory=list)

    def add_user_message(self, content: str) -> None:
        """记录一条用户消息"""
        self.messages.append({"role": "user", "content": content})

    def add_assistant_message(self, content: str) -> None:
        """记录一条 Agent 回复"""
        self.messages.append({"role": "assistant", "content": content})

    def to_dict(self) -> dict[str, Any]:
        """
        序列化为 dict（用于 Redis 存储）。

        为什么用 asdict 而不是 json.dumps？
        asdict 是 dataclass 内置的递归序列化，自动处理嵌套结构。
        json.dumps 需要手动处理 dataclass → dict 的转换。

        注意：user_profile 被排除——画像属于 SQLite 的长期记忆，
        每次执行从数据库读最新值，不走 Redis 会话存储。
        """
        data = asdict(self)
        data.pop("user_profile", None)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionMemory":
        """
        从 dict 反序列化（从 Redis 取出时用）。

        需要手动处理 messages 字段的默认值——Redis 存的 JSON
        可能不包含 messages 键（旧数据兼容）。
        同时过滤未知字段（未来版本加的字段，旧版本反序列化时忽略）。
        """
        # 只保留 dataclass 已知的字段，忽略额外键
        from dataclasses import fields
        known = {f.name for f in fields(cls)}
        data = {k: v for k, v in data.items() if k in known}

        if "messages" not in data:
            data["messages"] = []
        # 旧数据兼容：没有 interview 字段时给默认值
        if "interview_mode" not in data:
            data["interview_mode"] = None
        if "interview_round" not in data:
            data["interview_round"] = 0
        if "user_profile" not in data:
            data["user_profile"] = None
        if "summary" not in data:
            data["summary"] = None
        if "summarized_count" not in data:
            data["summarized_count"] = 0
        if "search_result" not in data:
            data["search_result"] = None
        if "search_sources" not in data:
            data["search_sources"] = []
        return cls(**data)