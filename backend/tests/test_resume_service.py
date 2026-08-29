"""
ResumeService 单测（断言式，注入 mock LLM，不打真实 API）

验证 analyze() 两件事：
1. 返回 LLM 的内容
2. 简历原文被正确渲染进 prompt（防止「service 吞了输入」这类 bug）
"""

from unittest.mock import MagicMock
from backend.app.schemas.resume import ResumeAnalyzeRequest
from backend.app.schemas.chat import ChatResult
from backend.app.services.resume_service import ResumeService


def _mock_llm(content="分析结果"):
    llm = MagicMock()
    llm.chat.return_value = ChatResult(
        content=content, model="mock", elapsed=0.0,
        prompt_tokens=0, completion_tokens=0, total_tokens=0,
    )
    return llm


def test_analyze_returns_llm_content():
    llm = _mock_llm()
    service = ResumeService(llm=llm)
    result = service.analyze(ResumeAnalyzeRequest(resume="张三 软件工程"))
    assert result == "分析结果"


def test_analyze_injects_resume_into_prompt():
    llm = _mock_llm()
    service = ResumeService(llm=llm)
    service.analyze(ResumeAnalyzeRequest(resume="张三 熟悉 FastAPI"))
    # 简历原文应被渲染进 user_prompt
    user_prompt = llm.chat.call_args.kwargs["user_prompt"]
    assert "张三 熟悉 FastAPI" in user_prompt
