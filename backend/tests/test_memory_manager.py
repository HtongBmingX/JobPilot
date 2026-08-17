from backend.app.memory.memory_manager import MemoryManager


def test_memory_manager():
    manager = MemoryManager()

    print("=" * 50)
    print("1. 创建两个 Session")

    session1 = manager.create_session("user001")
    session2 = manager.create_session("user002")

    print(session1)
    print(session2)

    print("=" * 50)
    print("2. 分别写入数据")

    session1.resume = "张三的软件工程简历"
    session2.resume = "李四的AI算法简历"

    print(session1.resume)
    print(session2.resume)

    print("=" * 50)
    print("3. 再次获取 Session")

    s1 = manager.get_session("user001")
    s2 = manager.get_session("user002")

    print(s1.resume)
    print(s2.resume)

    print("=" * 50)
    print("4. 删除 user001")

    manager.delete_session("user001")

    try:
        manager.get_session("user001")
    except KeyError as e:
        print(e)

    print("user002 仍然存在：")
    print(manager.get_session("user002").resume)

    print("=" * 50)
    print("5. 清空所有 Session")

    manager.clear()

    try:
        manager.get_session("user002")
    except KeyError as e:
        print(e)


if __name__ == "__main__":
    test_memory_manager()