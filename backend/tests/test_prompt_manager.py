from backend.app.prompts.prompt_manager import PromptManager


def test_get_prompt():
    manager = PromptManager()
    prompt = manager.get_prompt("resume_analyze")
    assert isinstance(prompt, str)
    assert len(prompt) > 0


def test_get_prompt_cached():
    """第二次获取走缓存，返回同一对象"""
    manager = PromptManager()
    p1 = manager.get_prompt("resume_analyze")
    p2 = manager.get_prompt("resume_analyze")
    assert p1 == p2


def test_get_prompt_missing_raises():
    """不存在的模板抛 FileNotFoundError"""
    manager = PromptManager()
    try:
        manager.get_prompt("不存在的模板")
        assert False, "应当抛出 FileNotFoundError"
    except FileNotFoundError:
        pass


def test_render_prompt():
    """渲染 {{变量}} 占位符"""
    manager = PromptManager()
    rendered = manager.render_prompt("resume_analyze", resume="张三的简历")
    assert "张三的简历" in rendered


if __name__ == "__main__":
    test_get_prompt()