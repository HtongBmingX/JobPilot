from typing import Any

from pydantic import BaseModel, Field


class Plan(BaseModel):
    """
    Planner 的输出。
    """

    thought: str = Field(
        description="模型的思考过程"
    )

    action: str = Field(
        description="下一步调用的 Tool"
    )

    action_input: dict[str, Any] = Field(
        default_factory=dict,
        description="Tool 的输入参数"
    )