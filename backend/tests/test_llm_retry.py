from unittest.mock import patch, MagicMock
from backend.app.services.llm_service import LLMService
from backend.app.core.exceptions import LLMServiceError


def test_retry_then_success():
    svc = LLMService()

    class Flaky:
        def __init__(self):
            self.n = 0
        def __call__(self, *a, **k):
            self.n += 1
            if self.n < 3:
                raise TimeoutError(f"fake timeout #{self.n}")
            resp = MagicMock()
            resp.choices = [MagicMock()]
            resp.choices[0].message.content = "OK"
            resp.model = "m"
            resp.usage = None
            return resp

    fake = Flaky()
    with patch.object(svc.client.chat.completions, "create", side_effect=fake):
        result = svc.chat(system_prompt="s", user_prompt="u")
    assert result.content == "OK"


def test_retry_exhausted():
    svc = LLMService()
    with patch.object(svc.client.chat.completions, "create",
                      side_effect=RuntimeError("always fail")):
        try:
            svc.chat(system_prompt="s", user_prompt="u")
            assert False, "应当抛出异常"
        except LLMServiceError as e:
            # 代码现在抛自定义的 LLMServiceError（不是原始 RuntimeError）
            assert "always fail" in str(e)


if __name__ == "__main__":
    test_retry_then_success()
    test_retry_exhausted()
