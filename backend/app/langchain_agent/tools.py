"""
LangChain 版 Tool 定义

迁移映射：
  手写 BaseTool + ToolRegistry  →  LangChain @tool 装饰器
  ResumeTool.run(resume=...)     →  analyze_resume(resume)
  JDTool.run(jd=...)             →  analyze_jd(jd)
  MatchTool.run(resume_analysis=..., jd_analysis=...)
                                  →  match_position(resume_analysis, jd_analysis)

为什么用 @tool 装饰器而不是继承 BaseTool？
- LangChain 的 @tool 是声明式 API：把普通 Python 函数标记为 Tool
- 比手写类更简洁——不需要 name/description/parameters 属性
- LangChain Agent 可以直接用这些函数作为工具

兼容性：这三个函数的实现调用的还是手写的 Service 层
（ResumeService / JDService / MatchService），
所以 LLM 调 Tool 时得到的分析和手写版完全一致。
"""

from langchain_core.tools import tool
from backend.app.schemas.resume import ResumeAnalyzeRequest
from backend.app.schemas.jd import JDAnalyzeRequest
from backend.app.schemas.match import MatchRequest
from backend.app.services.resume_service import ResumeService
from backend.app.services.jd_service import JDService
from backend.app.services.match_service import MatchService
from backend.app.core.logger import logger

# 复用已有的 Service 层——不改业务逻辑
_resume_service = ResumeService()
_jd_service = JDService()
_match_service = MatchService()


@tool
def analyze_resume(resume: str) -> str:
    """
    分析候选人简历。
    需要提供完整的简历原文。
    返回结构化的分析结果，包括优点、不足和优化建议。
    """
    logger.info("LangChain Tool: analyze_resume")
    request = ResumeAnalyzeRequest(resume=resume)
    return _resume_service.analyze(request)


@tool
def analyze_jd(jd: str) -> str:
    """
    分析岗位描述（JD）。
    需要提供完整的 JD 原文。
    返回结构化的分析结果，包括岗位职责、核心技能、加分项等。
    """
    logger.info("LangChain Tool: analyze_jd")
    request = JDAnalyzeRequest(jd=jd)
    return _jd_service.analyze(request)


@tool
def match_position(resume_analysis: str, jd_analysis: str) -> str:
    """
    基于已有的简历分析和 JD 分析结果，做岗位匹配。
    需要先完成 resume 和 jd 分析。
    返回匹配度百分制评分、匹配亮点、差距分析和提升建议。
    """
    logger.info("LangChain Tool: match_position")
    request = MatchRequest(
        resume_analysis=resume_analysis,
        jd_analysis=jd_analysis,
    )
    return _match_service.analyze(request)


# 工具列表——Agent 初始化时注册
ALL_TOOLS = [analyze_resume, analyze_jd, match_position]
