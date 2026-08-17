# 当前项目结构（v0.6.0）

> 最后更新：2026-07-23

## 后端

backend/
│
├── main.py                      # FastAPI 入口：6 个端点（手写版同步+流式 / LangChain版同步+流式 / upload / health），CORS + 限流 + 异常处理
├── requirements.txt             # 依赖（含 LangChain / Redis / hiredis）
├── .env                         # 环境变量（API Key + Redis 配置）
├── .env.example                 # 环境变量模板（含 Redis 可选配置）
│
├── app/
│   ├── core/
│   │   ├── config.py            # Pydantic Settings 配置中心（含 LLM 超时/重试配置）
│   │   ├── logger.py            # 企业级日志（控制台 + 文件）
│   │   ├── exceptions.py        # 自定义异常体系（JobPilotError 基类 + 5 个子类，各带 HTTP status_code）
│   │   ├── error_handlers.py    # 全局异常处理器（在 CORS 之后注册，不拦截 OPTIONS）
│   │   ├── redis_client.py      # Redis 客户端封装（连接池单例 + 懒加载 + 优雅降级）
│   │   └── rate_limit.py        # 固定窗口限流（INCR + EXPIRE），FastAPI Depends 注入
│   │
│   ├── prompts/
│   │   ├── prompt_manager.py    # 模板加载 + 缓存 + 渲染（{{变量}} 替换）
│   │   └── templates/
│   │       ├── system.md        # System Prompt（资深 HR 角色）
│   │       ├── planner.md       # Planner 决策指令（精简版——状态机已迁移到代码）
│   │       ├── synthesize.md    # 最终总结指令（含对话历史占位符）
│   │       ├── resume_analyze.md
│   │       ├── jd_analyze.md
│   │       ├── match_analyze.md
│   │       └── interview.md     # 面试建议模板（待实现）
│   │
│   ├── schemas/
│   │   ├── chat.py              # ChatResult（content, model, elapsed, tokens）
│   │   ├── plan.py              # Plan（thought, action, action_input）
│   │   ├── resume.py            # ResumeAnalyzeRequest
│   │   ├── jd.py                # JDAnalyzeRequest
│   │   └── match.py             # MatchRequest
│   │
│   ├── services/
│   │   ├── base_service.py      # 公共 _chat() 封装（PromptManager + LLMService）
│   │   ├── llm_service.py       # DeepSeek 调用（chat + chat_stream，重试+退避）
│   │   ├── resume_service.py    # analyze()
│   │   ├── jd_service.py        # analyze()
│   │   └── match_service.py     # analyze()
│   │
│   ├── tools/
│   │   ├── base_tool.py         # BaseTool 抽象类
│   │   ├── registry.py          # ToolRegistry 注册中心（register/get/exists/build_prompt）
│   │   ├── resume_tool.py       # 简历分析 Tool
│   │   ├── jd_tool.py           # JD 分析 Tool
│   │   ├── match_tool.py        # 岗位匹配 Tool
│   │   └── ingest_tool.py       # PDF/DOCX 解析（/upload 直接调用，不注册）
│   │
│   ├── memory/
│   │   ├── session_memory.py    # 单会话数据（业务记忆 + 对话记忆 + to_dict/from_dict 序列化）
│   │   ├── token_budget.py      # Token 预算控制器（近期优先截断策略）
│   │   ├── redis_store.py       # Redis 版会话存储（JSON 序列化，24h TTL 自动过期）
│   │   └── memory_manager.py    # 多会话管理（Redis 优先 + 内存 fallback 双路径）
│   │
│   ├── agent/
│   │   ├── planner.py           # LLM 决策器（精简版——规则由 AgentStateMachine 负责）
│   │   ├── agent_state.py       # 代码级状态机（AgentState + AgentStateMachine + 关键词检测）
│   │   └── jobpilot_agent.py    # 手写 ReAct 循环主体（execute + execute_stream + 状态机集成）
│   │
│   ├── langchain_agent/         # LangChain 版 Agent（Phase 4）
│   │   ├── llm.py               # ChatOpenAI 包装器（chat_sync + chat_stream）
│   │   ├── tools.py             # @tool 装饰器的三个工具函数
│   │   └── agent.py             # LangChainAgent（create_react_agent + InMemorySaver）
│   │
│   └── logs/                    # 日志输出目录
│
│
└── tests/
    ├── test_agent_loop.py       # 诊断测试（mock 隔离 Agent 循环 + Planner 决策）
    ├── test_agent.py            # Agent 集成测试
    ├── test_planner.py          # Planner 独立测试
    ├── test_plan.py             # Plan schema 测试
    ├── test_prompt_manager.py   # PromptManager 测试
    ├── test_resume_service.py   # ResumeService 测试
    ├── test_jd_service.py       # JDService 测试
    ├── test_match_service.py    # MatchService 测试
    ├── test_llm_service.py      # LLMService 测试
    ├── test_llm_retry.py        # LLM 重试逻辑测试（mock）
    ├── test_memory_manager.py   # MemoryManager 测试
    ├── test_session_memory.py   # SessionMemory 测试
    └── test_tools.py            # Tool 注册 + 提示词构建测试

---

## 前端（v1.0 UI）

frontend/
│
├── package.json                 # 依赖：vue, marked, @vitejs/plugin-vue, vite
├── vite.config.js               # vue 插件 + dev proxy（/agent → :8000, /upload → :8000）
├── index.html                   # SPA 挂载点 + 全局 CSS reset
├── dist/                        # 生产构建产物
│
└── src/
    ├── main.js                  # 创建 + 挂载 Vue 应用
    ├── App.vue                  # 根组件（编排层：Chat 区 + Input 区 + 状态管理）
    ├── composables/
    │   └── useAgent.js          # Agent 交互 Composable（状态 + uploadFile + sendMessage + SSE 消费）
    ├── components/
    │   ├── ChatBubble.vue       # 单条对话气泡（user 蓝色靠右 / assistant 白色靠左 + Markdown 渲染）
    │   ├── ThinkChain.vue       # Agent 思考链可视化（⏳ 正在分析 → ✅ 已完成）
    │   └── InputPanel.vue       # 输入面板（文件上传 + 简历/JD 编辑 + 问题输入 + 发送按钮）
    └── utils/
        └── markdown.js          # Markdown 渲染（marked.parse + XSS sanitize）

---

## 基础设施

├── docker-compose.yml           # Redis 7 Alpine（AOF 持久化 + 数据卷）
├── logs/                        # 根级日志目录
└── docs/                        # 开发文档
    ├── development_framework.md # 完整开发路线图（6 Phase / 20+ Steps）
    ├── architecture.md          # 架构设计
    ├── api_design.md            # API 设计文档
    ├── project_structure.md     # 本文档
    ├── changelog.md             # 变更日志（v0.1.0 → v0.6.0）
    ├── development_log.md       # 开发日志（Day 1-16，学习记录）
    └── roadmap.md               # 技术蓝图 + 演进路线
