from pydantic import BaseModel


class MatchRequest(BaseModel):
    """
    岗位匹配请求
    """

    resume_analysis: str

    jd_analysis: str