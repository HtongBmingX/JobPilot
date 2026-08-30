"""
MCP Client 适配层 —— 把 MCP Server 暴露的工具，动态包装成 JobPilot 的 BaseTool。

为什么做这一层？
JobPilot 的工具调用演进线是：手写 BaseTool → LangChain @tool → MCP Client。
三者回答的是同一个问题「Agent 怎么调用工具」，只是抽象层次不同：
- BaseTool：自己定义工具（name/description/parameters/run），完全可控
- @tool：框架的声明式封装
- MCP：协议的标准化——把「工具从哪来」和「Agent 怎么用工具」解耦

对 JobPilot 来说，MCP 工具只是 ToolRegistry 的另一种「来源」。
Planner / AgentStateMachine 看到的仍然是 BaseTool，无感知。

架构：

    MCP Server（外部，如 GitHub）
          │  MCP 协议（stdio，本地子进程）
          ▼
    MCPClientManager ──► 发现工具列表，动态生成 BaseTool 子类
          │
          ▼
    ToolRegistry.register() ──► Planner 像调 search 一样调它

关键设计决策（面试要讲）：
1. 动态包装：MCP 工具用 JSON Schema 描述参数，我动态生成 BaseTool 子类，
   而不是为每个工具手写一个类——这是「协议标准化」带来的好处（N+M 而非 N×M）。
2. async/sync 桥接：mcp SDK 是 asyncio 的，而 JobPilotAgent.execute() 是同步 def。
   这里用 asyncio.run() 桥接，和之前处理 LangChain astream_events 的阻抗是同一类问题。
   MVP 用 asyncio.run() 简单可靠；未来若要高并发，再给 Agent 加 async 执行路径。
3. 优雅降级：未配置 GitHub PAT 时，MCP 工具不注册、Agent 正常运行——和 RAG 未配置
   DashScope key 时的降级一致，MCP 是「加分项」不是「必需品」。
"""

from __future__ import annotations

import asyncio
from typing import Any

from backend.app.core.config import settings
from backend.app.core.logger import logger
from backend.app.tools.base_tool import BaseTool


class MCPToolAdapter(BaseTool):
    """
    把单个 MCP 工具包装成 BaseTool。

    run() 是同步的（BaseTool 契约），内部用 asyncio.run() 调 MCP Server。
    """

    # 标记为「外部工具」——AgentStateMachine 和 Agent 路由时据此识别
    is_external = True

    def __init__(self, name: str, description: str, parameters: list[str], call_fn):
        self.name = name
        self.description = description
        self.parameters = parameters
        # call_fn: 异步函数，接收 kwargs dict，返回工具结果字符串
        self._call_fn = call_fn

    def run(self, **kwargs) -> str:
        try:
            return asyncio.run(self._call_fn(kwargs))
        except Exception as e:
            logger.error(f"MCP 工具 {self.name} 调用失败：{e}")
            return f"（MCP 工具 {self.name} 调用失败：{e}）"


class MCPClientManager:
    """
    管理一个或多个 MCP Server 的连接，把它们的工具暴露成 BaseTool。

    用法：
        manager = MCPClientManager()
        tools = await manager.connect_github()   # 返回 [BaseTool, ...]
        for t in tools:
            registry.register(t)
    """

    def __init__(self):
        self._tools: list[BaseTool] = []

    @property
    def available(self) -> bool:
        """是否配置了 GitHub PAT（未配置则 MCP 不可用，优雅降级）"""
        return bool(settings.GITHUB_PAT)

    async def connect_github(self) -> list[BaseTool]:
        """
        连接 GitHub MCP Server（stdio 方式），把它的工具包装成 BaseTool。

        前置条件：
        - 安装 mcp SDK + server-github：pip install mcp
        - 环境变量 GITHUB_PERSONAL_ACCESS_TOKEN（只读权限即可）

        实现说明：用官方 mcp SDK 的 stdio_client + ClientSession，
        列出工具后对每个工具生成一个 MCPToolAdapter。
        """
        if not self.available:
            logger.warning("未配置 GITHUB_PAT，跳过 MCP GitHub 工具注册")
            return []

        # 延迟导入：mcp 是重依赖，只有真正要用时才 import（和 LangChain 懒加载同理）
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
        except ImportError:
            logger.warning("未安装 mcp SDK（pip install mcp），MCP 不可用")
            return []

        server_params = StdioServerParameters(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-github"],
            env={"GITHUB_PERSONAL_ACCESS_TOKEN": settings.GITHUB_PAT},
        )

        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools_result = await session.list_tools()
                    adapters = self._build_adapters(tools_result.tools, session)
                    self._tools.extend(adapters)
                    logger.info(f"MCP GitHub 工具注册成功：{len(adapters)} 个")
                    return adapters
        except Exception as e:
            logger.error(f"MCP GitHub Server 连接失败：{e}")
            return []

    def _build_adapters(self, tools: list, session) -> list[BaseTool]:
        """把 MCP 工具列表（JSON Schema）转成 BaseTool 列表。"""
        # 只读白名单：求职场景只需要「查 repo/代码/用户/issue」，不需要写操作。
        # 写工具（create/push/fork/merge 等）暴露给 LLM 决策是安全风险——
        # 即使当前 PAT 只读，也不该把写能力交给概率模型。
        READONLY_WHITELIST = {
            "search_repositories", "get_file_contents", "list_commits",
            "list_issues", "search_code", "search_issues", "search_users",
            "get_issue", "get_pull_request", "list_pull_requests",
            "get_pull_request_files", "get_pull_request_status",
            "get_pull_request_comments", "get_pull_request_reviews",
            "get_commit", "list_branches", "get_tag",
        }
        adapters = []
        for t in tools:
            name = getattr(t, "name", "")
            if name not in READONLY_WHITELIST:
                logger.info(f"MCP 工具 {name} 不在只读白名单，跳过注册（安全过滤）")
                continue
            description = getattr(t, "description", "") or ""
            # 从 inputSchema 提取参数名列表
            schema = getattr(t, "inputSchema", None) or {}
            properties = schema.get("properties", {}) if isinstance(schema, dict) else {}
            parameters = list(properties.keys()) if isinstance(properties, dict) else []

            async def call_fn(kwargs, _tool_name=name):
                result = await session.call_tool(_tool_name, kwargs)
                # call_tool 返回的 content 是列表，提取文本
                contents = getattr(result, "content", []) or []
                texts = []
                for c in contents:
                    if hasattr(c, "text"):
                        texts.append(c.text)
                    elif isinstance(c, dict) and "text" in c:
                        texts.append(c["text"])
                return "\n".join(texts) if texts else "（无返回内容）"

            adapters.append(MCPToolAdapter(name, description, parameters, call_fn))

        return adapters

    def list_tools(self) -> list[BaseTool]:
        """返回已连接的 MCP 工具（可能为空，取决于是否配置 PAT 且连接成功）"""
        return list(self._tools)


def build_mcp_tools() -> list[BaseTool]:
    """
    同步入口：连接 MCP Server 并返回工具列表。

    供 main.py 启动时调用（懒加载），内部桥接异步连接。
    未配置 PAT / 未装 SDK / 连接失败时返回空列表，不影响主流程。

    关键：main.py 在 uvicorn 里 import 时，已经处于运行中的事件循环，
    不能直接 asyncio.run()（会报「cannot be called from a running event loop」）。
    所以先尝试拿当前事件循环，拿不到才用 asyncio.run()。
    """
    manager = MCPClientManager()
    if not manager.available:
        return []
    try:
        # 已在事件循环内（uvicorn）→ 用新线程跑，避免嵌套事件循环
        try:
            asyncio.get_running_loop()
            import threading
            result: list[BaseTool] = []
            def _run():
                result.extend(asyncio.run(manager.connect_github()))
            t = threading.Thread(target=_run)
            t.start()
            t.join(timeout=30)
            return result
        except RuntimeError:
            # 不在事件循环内（同步测试/脚本）→ 直接用 asyncio.run
            return asyncio.run(manager.connect_github())
    except Exception as e:
        logger.error(f"MCP 工具加载失败：{e}")
        return []
