"""系统状态 Pydantic schema"""

from pydantic import BaseModel


class SystemStatus(BaseModel):
    """GET /status 返回的系统状态快照"""
    redis_connected: bool = False
    agent_mode: str = "react"         # "react" | "langchain" | "langgraph"
