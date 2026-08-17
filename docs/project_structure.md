# 项目结构（v0.9.3）

> 最后更新：2026-08-17

## 后端

```
backend/
├── main.py                      # FastAPI 入口：20 个端点（auth/agent/applications/resumes/profile/upload/status）
├── requirements.txt             # 依赖（FastAPI/Redis/LangChain/SQLAlchemy/alembic/pytest）
├── .env.example                 # 环境变量模板（DeepSeek + DashScope key）
├── alembic.ini                  # 数据库迁移配置
├── alembic/                     # 迁移脚本（baseline + resumes/user_profiles）
├── pytest.ini                   # 测试配置
│
├── app/
│   ├── core/
│   │   ├── config.py            # Pydantic Settings（LLM + Redis + DashScope 配置）
│   │   ├── database.py          # SQLAlchemy 引擎 + Session 工厂
│   │   ├── auth.py              # JWT + bcrypt 鉴权（access/refresh token）
│   │   ├── logger.py            # 日志（控制台 + 文件）
│   │   ├── exceptions.py        # 自定义异常体系
│   │   ├── error_handlers.py    # 全局异常处理器
│   │   ├── redis_client.py      # Redis 连接池单例 + 优雅降级
│   │   └── rate_limit.py        # 固定窗口限流
│   │
│   ├── agent/
│   │   ├── jobpilot_agent.py    # 手写 ReAct 循环主体（execute + execute_stream）
│   │   ├── agent_state.py       # 代码级状态机 + 意图关键词检测
│   │   └── planner.py           # LLM 决策器（从 allowed 选择 + 提取参数）
│   │
│   ├── tools/
│   │   ├── base_tool.py         # BaseTool 抽象类
│   │   ├── registry.py          # ToolRegistry 注册中心
│   │   ├── resume_tool.py       # 简历分析
│   │   ├── jd_tool.py           # JD 分析
│   │   ├── match_tool.py        # 岗位匹配
│   │   ├── interview_tool.py    # 面试模拟（三模式 + 多轮）
│   │   ├── search_tool.py       # RAG 知识库检索
│   │   └── ingest_tool.py       # PDF/DOCX 解析（/upload 直接调用）
│   │
│   ├── memory/
│   │   ├── session_memory.py    # 会话数据（业务记忆 + 对话 + 画像 + 摘要 + 序列化）
│   │   ├── memory_manager.py    # 多会话管理（Redis 优先 + 内存 fallback）
│   │   ├── redis_store.py       # Redis 会话存储（24h TTL）
│   │   ├── token_budget.py      # Token 预算（近期优先截断 + 摘要压缩）
│   │   └── conversation_summarizer.py  # LLM 增量摘要
│   │
│   ├── rag/
│   │   ├── rag_pipeline.py      # RAG 统一入口
│   │   ├── embedding.py         # 千问 text-embedding-v3（query/document 非对称）
│   │   ├── vector_store.py      # 纯 Python 向量存储（余弦相似度 + JSON 持久化）
│   │   ├── hybrid_searcher.py   # BM25 + 向量 + RRF 融合
│   │   ├── knowledge_docs.py    # 知识库数据（23 篇 / 7 方向）
│   │   └── build_knowledge_base.py  # 知识库构建脚本
│   │
│   ├── models/                  # SQLAlchemy ORM
│   │   ├── user.py              # 用户
│   │   ├── application.py       # 投递记录
│   │   ├── resume.py            # 简历库
│   │   └── user_profile.py      # 用户画像
│   │
│   ├── repositories/            # Repository 模式
│   │   ├── user_repo.py
│   │   ├── application_repo.py
│   │   ├── resume_repo.py
│   │   └── user_profile_repo.py
│   │
│   ├── schemas/                 # Pydantic 请求/响应
│   │   ├── user.py / application.py / resume_library.py / user_profile.py
│   │   ├── chat.py / plan.py / match.py / status.py 等
│   │
│   ├── services/                # 业务逻辑层
│   │   ├── llm_service.py       # DeepSeek 调用（chat + chat_stream + 重试）
│   │   ├── base_service.py      # 公共 _chat 封装
│   │   ├── resume_service.py / jd_service.py / match_service.py
│   │   └── interview_service.py
│   │
│   ├── prompts/
│   │   ├── prompt_manager.py    # 模板加载 + 缓存 + 渲染
│   │   └── templates/           # 9 个 prompt 模板
│   │
│   ├── langchain_agent/         # LangChain 版（对比用）
│   │   ├── agent.py / llm.py / tools.py
│   │
│   ├── langgraph_agent/         # LangGraph 状态定义（预留）
│   │   └── state.py
│   │
│   └── evaluation/              # 评测体系
│       ├── runner.py            # 评测执行器（基础 + RAG 两套）
│       ├── test_cases.py        # 基础能力用例
│       ├── rag_test_cases.py    # RAG 知识库问答用例
│       ├── deterministic_metrics.py  # 确定性指标（触发率/命中率/标注率）
│       └── metrics/             # faithfulness/relevancy/recall（LLM 判定版）
│
└── tests/                       # 47 个测试
    ├── test_agent_state.py      # 状态机路由 + 关键词检测
    ├── test_token_budget.py     # Token 预算 + 截断
    ├── test_session_memory_serialization.py  # 序列化 + 兼容
    ├── test_rag_search.py       # 向量存储 + BM25 + RRF
    └── ... 其他测试
```

## 前端

```
frontend/
├── package.json                 # vue + marked + vitest
├── vite.config.js               # dev proxy（7 条代理到 :8000）
├── vitest.config.js             # 测试配置
├── index.html                   # SPA 挂载点
├── nginx.conf                   # Nginx 反代（SSE 支持）
├── Dockerfile                   # 多阶段构建
│
└── src/
    ├── main.js                  # 入口（import tokens.css）
    ├── App.vue                  # 根组件（视图切换 + 编排）
    ├── styles/tokens.css        # 设计 Token（颜色/间距/字号/圆角变量）
    ├── composables/             # 6 个 composable
    │   ├── useAgent.js          # 多会话 + SSE + 鉴权
    │   ├── useApplications.js / useResumes.js / useProfile.js
    │   ├── useStatus.js / useToast.js
    ├── components/              # 11 个组件
    │   ├── ChatBubble.vue / ThinkChain.vue / InputPanel.vue
    │   ├── ConversationSidebar.vue / JobBoard.vue / JobCard.vue
    │   ├── ApplicationDetailModal.vue / ProfileModal.vue
    │   ├── StatusBar.vue / ToastContainer.vue / AboutView.vue
    └── utils/
        ├── application.js       # 纯函数（分数解析/色阶/日期）
        ├── markdown.js          # Markdown + XSS 清洗
        └── __tests__/           # 前端测试
```

## 基础设施

```
docker-compose.yml               # 三服务（redis + backend + frontend）
backend/Dockerfile               # 后端多阶段构建
frontend/Dockerfile              # 前端 node + nginx
docs/                            # 文档
    ├── architecture.md          # 架构设计
    ├── api_design.md            # API 文档
    ├── project_structure.md     # 本文档
    ├── roadmap.md               # 技术蓝图（最新）
    ├── changelog.md             # 变更日志
    └── development_log.md       # 开发日志（Day 1-32）
```
