from pydantic import BaseModel


class ResumeAnalyzeRequest(BaseModel):
    """
    简历分析请求
    """

    resume: str


class ResumeAnalyzeResponse(BaseModel):
    """
    简历分析响应
    """

    result: str