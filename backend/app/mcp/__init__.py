"""MCP Client 适配层包。

把 MCP Server（如 GitHub）暴露的工具，动态包装成 JobPilot 的 BaseTool，
注册进 ToolRegistry，让 Planner 像调本地工具一样调外部工具。
"""
