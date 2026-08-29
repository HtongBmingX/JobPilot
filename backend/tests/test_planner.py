"""
Planner 单测（断言式）

重点测 _extract_json 的容错解析——这是 Planner 的核心难点（LLM 输出格式不稳定）。
纯静态方法，无需 mock LLM。
"""

from backend.app.agent.planner import Planner
from backend.app.core.exceptions import LLMResponseError


def test_extract_json_direct():
    data = Planner._extract_json('{"thought": "t", "action": "resume", "action_input": {}}')
    assert data["action"] == "resume"


def test_extract_json_with_markdown_fence():
    text = '```json\n{"thought": "t", "action": "jd", "action_input": {}}\n```'
    data = Planner._extract_json(text)
    assert data["action"] == "jd"


def test_extract_json_with_extra_text_around():
    text = '好的，我的决策是：{"thought": "t", "action": "match", "action_input": {}} 以上就是。'
    data = Planner._extract_json(text)
    assert data["action"] == "match"


def test_extract_json_empty_raises():
    try:
        Planner._extract_json("")
        assert False, "应当抛出 LLMResponseError"
    except LLMResponseError:
        pass


def test_extract_json_garbage_raises():
    try:
        Planner._extract_json("这不是 JSON")
        assert False, "应当抛出 LLMResponseError"
    except LLMResponseError:
        pass
