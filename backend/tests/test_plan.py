from backend.app.schemas.plan import Plan


def main():

    plan = Plan(
        thought="分析简历",
        action="resume",
        action_input={
            "resume": "我是软件工程专业..."
        }
    )

    print(plan)

    print(plan.model_dump())


if __name__ == "__main__":
    main()