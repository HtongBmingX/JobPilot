"""
MatchService 单测（断言式，注入 mock LLM，不打真实 API）
"""

from unittest.mock import MagicMock
from backend.app.schemas.match import MatchRequest
from backend.app.schemas.chat import ChatResult
from backend.app.services.match_service import MatchService


def _mock_llm(content="匹配结果"):
    llm = MagicMock()
    llm.chat.return_value = ChatResult(
        content=content, model="mock", elapsed=0.0,
        prompt_tokens=0, completion_tokens=0, total_tokens=0,
    )
    return llm


def test_analyze_returns_llm_content():
    llm = _mock_llm()
    service = MatchService(llm=llm)
    result = service.analyze(MatchRequest(resume_analysis="简历分析", jd_analysis="JD 分析"))
    assert result == "匹配结果"


def test_analyze_injects_both_analyses_into_prompt():
    llm = _mock_llm()
    service = MatchService(llm=llm)
    service.analyze(MatchRequest(resume_analysis="简历分析内容", jd_analysis="JD 分析内容"))
    user_prompt = llm.chat.call_args.kwargs["user_prompt"]
    assert "简历分析内容" in user_prompt
    assert "JD 分析内容" in user_prompt
