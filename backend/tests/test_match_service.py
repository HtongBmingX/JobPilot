from backend.app.schemas.match import MatchRequest
from backend.app.services.match_service import MatchService


def test_match_analyze():
    """测试简历与岗位匹配"""

    service = MatchService()

    request = MatchRequest(
        resume_analysis="""
## 简历分析

候选人专业：软件工程（本科）

核心技能：
- Python
- C++
- FastAPI
- Git
- 深度学习基础
- AI Agent 开发

项目经验：
- JobPilot AI 求职助手
- 使用 FastAPI、DeepSeek API、React 开发

优势：
- Python 基础扎实
- 有 AI 项目开发经验
- 熟悉 RESTful API

不足：
- Docker 使用经验较少
- 数据库项目经验较少
""",
        jd_analysis="""
## 岗位分析

岗位：Python 后端开发工程师

核心技能：
- Python
- FastAPI
- MySQL
- Docker
- Git

学历要求：
本科及以上

经验要求：
1~3 年

岗位特点：
参与 AI 平台后端开发，负责 RESTful API 开发及 Agent 系统建设。
"""
    )

    result = service.analyze(request)

    print("=" * 60)
    print("岗位匹配分析")
    print("=" * 60)
    print(result)
    print("=" * 60)


if __name__ == "__main__":
    test_match_analyze()