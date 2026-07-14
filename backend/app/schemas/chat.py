from pydantic import BaseModel


class ChatResult(BaseModel):
    """
    LLM 调用结果
    """

    content: str          # 模型回复内容
    model: str            # 模型名称
    elapsed: float        # 调用耗时（秒）

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int