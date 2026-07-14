from backend.app.schemas.jd import JDAnalyzeRequest
from backend.app.services.jd_service import JDService


def test_jd_analyze():
    service = JDService()

    request = JDAnalyzeRequest(
        jd="""
岗位：Python后端开发工程师

岗位职责：
1. 负责AI平台后端开发；
2. 使用FastAPI构建RESTful API；
3. 参与LLM Agent系统开发；
4. 与前端协作完成业务开发。

任职要求：
1. 熟悉Python；
2. 熟悉FastAPI；
3. 熟悉MySQL；
4. 熟悉Git；
5. 有AI项目经验优先。
"""
    )

    result = service.analyze(request)

    print("=" * 60)
    print(result)
    print("=" * 60)


if __name__ == "__main__":
    test_jd_analyze()