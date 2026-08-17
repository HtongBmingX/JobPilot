from backend.app.memory.session_memory import SessionMemory


def test_session_memory():

    memory = SessionMemory()

    print(memory)

    memory.resume = "我是软件工程专业学生"

    memory.resume_analysis = "Python、FastAPI、AI Agent"

    print(memory)

    print("=" * 50)

    print(memory.resume)

    print(memory.resume_analysis)


if __name__ == "__main__":
    test_session_memory()