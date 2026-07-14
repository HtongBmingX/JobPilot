from backend.app.services.llm_service import LLMService


def test_chat():
    llm = LLMService()

    result = llm.chat(
        system_prompt="你是一名助手。",
        user_prompt="请介绍一下自己。"
    )

    print("=" * 50)
    print(result)


if __name__ == "__main__":
    test_chat()