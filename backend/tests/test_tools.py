"""
ToolRegistry 单测（断言式）
"""

from backend.app.tools.registry import ToolRegistry
from backend.app.tools.resume_tool import ResumeTool
from backend.app.tools.jd_tool import JDTool
from backend.app.tools.match_tool import MatchTool


def test_register_and_list():
    registry = ToolRegistry()
    registry.register(ResumeTool())
    registry.register(JDTool())
    registry.register(MatchTool())
    assert set(registry.list_tools()) == {"resume", "jd", "match"}
    assert len(registry) == 3


def test_get_and_exists():
    registry = ToolRegistry()
    registry.register(ResumeTool())
    assert registry.exists("resume")
    assert not registry.exists("interview")
    assert registry.get("resume").name == "resume"


def test_get_missing_raises_keyerror():
    registry = ToolRegistry()
    try:
        registry.get("不存在")
        assert False, "应当抛出 KeyError"
    except KeyError:
        pass


def test_remove():
    registry = ToolRegistry()
    registry.register(ResumeTool())
    registry.remove("resume")
    assert not registry.exists("resume")
    # 删除不存在的也不报错
    registry.remove("不存在")


def test_build_prompt_contains_all_tools():
    registry = ToolRegistry()
    registry.register(ResumeTool())
    registry.register(JDTool())
    prompt = registry.build_prompt()
    assert "resume" in prompt
    assert "jd" in prompt
    assert "工具名称" in prompt
