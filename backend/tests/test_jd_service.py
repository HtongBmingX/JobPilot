"""
JDService 单测（断言式，注入 mock LLM，不打真实 API）
"""

from unittest.mock import MagicMock
from backend.app.schemas.jd import JDAnalyzeRequest
from backend.app.schemas.chat import ChatResult
from backend.app.services.jd_service import JDService


def _mock_llm(content="JD 分析结果"):
    llm = MagicMock()
    llm.chat.return_value = ChatResult(
        content=content, model="mock", elapsed=0.0,
        prompt_tokens=0, completion_tokens=0, total_tokens=0,
    )
    return llm


def test_analyze_returns_llm_content():
    llm = _mock_llm()
    service = JDService(llm=llm)
    result = service.analyze(JDAnalyzeRequest(jd="Python 后端，3 年经验"))
    assert result == "JD 分析结果"


def test_analyze_injects_jd_into_prompt():
    llm = _mock_llm()
    service = JDService(llm=llm)
    service.analyze(JDAnalyzeRequest(jd="要求熟悉 FastAPI"))
    user_prompt = llm.chat.call_args.kwargs["user_prompt"]
    assert "要求熟悉 FastAPI" in user_prompt
