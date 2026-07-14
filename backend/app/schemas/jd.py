from pydantic import BaseModel


class JDAnalyzeRequest(BaseModel):
    """
    岗位描述分析请求
    """

    jd: str