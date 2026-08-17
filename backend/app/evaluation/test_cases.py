"""
评测用例集

每个用例包含：
- id: 唯一标识
- question: 用户提问
- resume: 简历文本
- jd: JD 文本
- sources: 期望的来源材料（用于计算 faithfulness 和 recall）
- expected_key_points: 回答中应包含的关键点（人工标注，用于手工验证）
"""

TEST_CASES = [
    {
        "id": "tc_001",
        "name": "简历分析-基础",
        "question": "分析我的简历，指出优缺点",
        "resume": """张三
软件工程专业，本科，2024 年毕业
技术栈：Python、FastAPI、Docker、MySQL、Redis
项目经历：
1. 电商订单系统：使用 FastAPI + MySQL 开发后端 API，支持订单创建、查询、退款。部署在 Docker 容器中。
2. 实时数据分析平台：使用 Python + Redis 做数据缓存层，降低数据库查询压力 60%。
实习经历：某互联网公司后端开发实习生（2023.06-2023.12），参与内部运维平台开发。""",
        "jd": "",
        "sources": "简历内容：张三，软件工程本科，2024 年毕业。技术栈 Python/FastAPI/Docker/MySQL/Redis。项目经验包括电商订单系统和实时数据分析平台。有后端开发实习经验（2023.06-2023.12）。",
        "expected_key_points": ["Python 技术栈", "FastAPI 后端", "有实习经验", "Docker 容器化"],
    },
    {
        "id": "tc_002",
        "name": "人岗匹配-Python后端",
        "question": "我的简历和这个 JD 匹配吗？",
        "resume": """张三
软件工程专业，本科，2024 年毕业
技术栈：Python、FastAPI、Docker、MySQL、Redis
项目经历：
1. 电商订单系统：FastAPI + MySQL 开发后端 API
2. 实时数据分析平台：Python + Redis 缓存层""",
        "jd": """Python 后端开发工程师
岗位要求：
- 3 年以上 Python 开发经验
- 熟悉 FastAPI 或 Django 框架
- 熟悉 MySQL、Redis 等数据库
- 了解 Docker 容器化部署
- 有微服务架构经验优先""",
        "sources": "简历：张三，软件工程本科，Python/FastAPI/Docker/MySQL/Redis 技术栈，有后端项目经验。JD：Python 后端开发，要求 3 年经验，FastAPI/Django，MySQL/Redis，Docker，微服务优先。",
        "expected_key_points": ["匹配度评分", "经验年限差距", "技术栈匹配程度", "微服务经验不足"],
    },
    {
        "id": "tc_003",
        "name": "追问-技能差距",
        "question": "我还缺什么技能？",
        "resume": "张三，软件工程本科，Python、FastAPI、Docker、MySQL、Redis",
        "jd": "Python 后端，要求 FastAPI/Django、MySQL/Redis、Docker、微服务",
        "sources": "简历：Python/FastAPI/Docker/MySQL/Redis。JD 要求：FastAPI/Django（满足）、MySQL/Redis（满足）、Docker（满足）、微服务（不满足）。",
        "expected_key_points": ["微服务经验不足", "技术栈大部分匹配"],
    },
    {
        "id": "tc_004",
        "name": "聊天模式-通用建议",
        "question": "自我介绍应该怎么写？",
        "resume": "",
        "jd": "",
        "sources": "通用求职知识：自我介绍应包含基本信息、核心技能、项目亮点、求职意向，控制在 1-2 分钟内。",
        "expected_key_points": ["基本信息", "核心技能", "项目亮点", "求职意向"],
    },
    {
        "id": "tc_005",
        "name": "边缘场景-无简历无JD",
        "question": "你好，你能帮我做什么？",
        "resume": "",
        "jd": "",
        "sources": "JobPilot 是一个 AI 求职助手，可以分析简历、分析 JD、做匹配评估、模拟面试。",
        "expected_key_points": ["简历分析", "JD 分析", "人岗匹配", "模拟面试"],
    },
]
