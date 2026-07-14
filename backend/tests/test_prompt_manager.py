from backend.app.prompts.prompt_manager import PromptManager


def test_get_prompt():
    manager = PromptManager()

    prompt = manager.get_prompt("resume")

    print("=" * 50)
    print("Prompt Content")
    print("=" * 50)
    print(prompt)


if __name__ == "__main__":
    test_get_prompt()