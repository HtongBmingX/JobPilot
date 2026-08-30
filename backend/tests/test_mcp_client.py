"""
MCP Client 适配层单测（断言式，mock 隔离，不依赖真实 MCP Server / GitHub）

覆盖：
1. MCPToolAdapter.run —— 异步 call_fn 被正确桥接（asyncio.run），返回结果字符串
2. MCPToolAdapter 异常 —— call_fn 抛错时返回错误文案，不向上抛
3. MCPToolAdapter.is_external —— 外部工具标记
4. MCPClientManager.available —— 未配置 GITHUB_PAT 时不可用
5. registry.list_external_tools —— 能识别外部工具
"""

import asyncio
from backend.app.mcp.client import MCPToolAdapter, MCPClientManager
from backend.app.tools.registry import ToolRegistry


async def _ok_call(kwargs: dict) -> str:
    return f"查询结果：{kwargs}"


async def _fail_call(kwargs: dict) -> str:
    raise ValueError("boom")


def test_mcp_tool_adapter_run():
    tool = MCPToolAdapter("gh_search", "搜索 GitHub 仓库", ["query"], _ok_call)
    result = tool.run(query="fastapi")
    assert "查询结果" in result
    assert "fastapi" in result


def test_mcp_tool_adapter_run_failure_returns_error_string():
    tool = MCPToolAdapter("gh_broken", "会失败", ["query"], _fail_call)
    result = tool.run(query="x")
    # 不向上抛异常，返回错误文案
    assert "调用失败" in result


def test_mcp_tool_adapter_is_external():
    tool = MCPToolAdapter("gh_search", "desc", ["query"], _ok_call)
    assert tool.is_external is True


def test_mcp_manager_not_available_without_pat(monkeypatch):
    # 强制把 GITHUB_PAT 设为空，模拟「未配置」的环境（不依赖真实 .env）
    monkeypatch.setattr("backend.app.mcp.client.settings.GITHUB_PAT", "")
    manager = MCPClientManager()
    # GITHUB_PAT 为空 → available False
    assert manager.available is False
    # connect_github 返回空列表（优雅降级，不抛异常）
    tools = asyncio.run(manager.connect_github())
    assert tools == []


def test_registry_lists_external_tools():
    registry = ToolRegistry()
    registry.register(MCPToolAdapter("gh_search", "desc", ["query"], _ok_call))
    # 本地工具（无 is_external 标记）不会被误判为外部工具
    from backend.app.tools.resume_tool import ResumeTool
    registry.register(ResumeTool())

    assert registry.list_external_tools() == ["gh_search"]


def test_state_machine_external_intent():
    from backend.app.agent.agent_state import _query_mentions_external
    assert _query_mentions_external("帮我看看这个公司的开源项目技术栈") is True
    assert _query_mentions_external("看看面试官的 github 仓库") is True
    # 知识库类问题不算外部意图
    assert _query_mentions_external("MySQL 索引为什么用 B+ 树") is False


def test_build_adapters_filters_write_tools():
    """
    只读白名单过滤：写操作工具（create/push/merge 等）不被注册，
    只保留查 repo/代码/用户的只读工具。这是安全设计——不把写能力交给 LLM。
    """
    from backend.app.mcp.client import MCPClientManager

    manager = MCPClientManager()

    class _FakeTool:
        def __init__(self, name, description="", schema=None):
            self.name = name
            self.description = description
            self.inputSchema = schema or {"properties": {}}

    class _FakeSession:
        async def call_tool(self, name, kwargs):
            return type("R", (), {"content": []})()

    tools = [
        _FakeTool("search_repositories", "查仓库", {"properties": {"query": {}}}),
        _FakeTool("get_file_contents", "读文件", {"properties": {"owner": {}, "repo": {}, "path": {}}}),
        _FakeTool("create_or_update_file", "写文件（危险）", {"properties": {}}),
        _FakeTool("push_files", "推送（危险）", {"properties": {}}),
        _FakeTool("merge_pull_request", "合并（危险）", {"properties": {}}),
    ]

    adapters = manager._build_adapters(tools, _FakeSession())
    names = [a.name for a in adapters]

    # 只读工具被保留
    assert "search_repositories" in names
    assert "get_file_contents" in names
    # 写工具被过滤
    assert "create_or_update_file" not in names
    assert "push_files" not in names
    assert "merge_pull_request" not in names


def test_build_adapters_extracts_parameters():
    """从 inputSchema 提取参数名列表，供 Planner 展示工具签名"""
    from backend.app.mcp.client import MCPClientManager

    manager = MCPClientManager()

    class _FakeTool:
        def __init__(self, name):
            self.name = name
            self.description = "查仓库"
            self.inputSchema = {"properties": {"query": {}, "per_page": {}}}

    class _FakeSession:
        async def call_tool(self, name, kwargs):
            return type("R", (), {"content": []})()

    adapters = manager._build_adapters([_FakeTool("search_repositories")], _FakeSession())
    assert adapters[0].parameters == ["query", "per_page"]
