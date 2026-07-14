from backend.app.schemas.resume import ResumeAnalyzeRequest
from backend.app.services.resume_service import ResumeService


def test_resume_analyze():
    """测试简历分析功能"""

    service = ResumeService()

    request = ResumeAnalyzeRequest(
        resume="""
姓名：张三

学校：大连理工大学
专业：软件工程

技能：
- Python
- C++
- FastAPI
- 深度学习

项目：
- JobPilot AI Agent
- 基于 FastAPI + DeepSeek + React
"""
    )

    result = service.analyze(request)

    print("=" * 60)
    print("简历分析结果：")
    print(result)
    print("=" * 60)


if __name__ == "__main__":
    test_resume_analyze()