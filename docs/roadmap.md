# JobPilot 项目开发进度与技术蓝图

> 本文档是项目的**正式技术蓝图**，记录已实现能力、当前开发状态，以及面向秋招的完整演进路线与高含金量技术选型。
> 最后更新：2026-08-14

---

## 已完成

### 阶段一：核心基础设施 ✅
- [x] FastAPI 项目初始化 + 配置管理（Pydantic Settings）
- [x] 日志系统（Logger，控制台 + 文件双通道）
- [x] LLMService 封装（OpenAI SDK 兼容 DeepSeek，重试+退避）
- [x] PromptManager 模块（模板加载 + 缓存 + {{变量}} 渲染）
- [x] Resume / JD / Match Service 层

### 阶段二：Agent 核心 ✅
- [x] ReAct Agent（手写循环：Planner + JobPilotAgent + Tool + Memory）
- [x] Tool Calling（resume / jd / match，ToolRegistry 注册中心）
- [x] Agent Memory（SessionMemory / MemoryManager，业务记忆与对话记忆分离）
- [x] Synthesize（基于 Memory 真实分析结果生成最终答案，消除幻觉）
- [x] Planner 状态机代码化（AgentStateMachine —— 代码确定规则，LLM 仅做语义选择）
- [x] FastAPI 业务端点（`/agent/run` + `/agent/run/stream`）

### 阶段三：体验层 ✅
- [x] SSE 流式输出（`LLMService.chat_stream()` → `execute_stream()` → `StreamingResponse`）
- [x] Markdown 前端渲染（marked.js + XSS sanitize）
- [x] 多轮对话（`SessionMemory.messages` + `TokenBudget` 控制器）
- [x] 思考链可视化（step_start / step_done 事件 + ThinkChain 组件）
- [x] 前端组件化（useAgent Composable + ChatBubble + ThinkChain + InputPanel）
- [x] Vite proxy 跨域方案

### 阶段四：架构层 ✅
- [x] Planner 状态机代码化（AgentStateMachine —— 从 prompt 规则迁移到 Python 代码）
- [x] 自定义异常体系（JobPilotError 基类 + 5 个子类，各带 HTTP status_code）
- [x] 全局错误处理（register_error_handlers，不拦截 CORS OPTIONS）
- [x] API 限流（固定窗口算法，Redis INCR + EXPIRE，FastAPI Depends 注入）
- [x] 文件摄入：`IngestTool`（PDF/DOCX 解析）+ `POST /upload` 端点

### 阶段五：数据层 ✅
- [x] Redis 客户端封装（连接池单例 + 懒加载 + 优雅降级）
- [x] Redis 版会话存储（SessionMemory → JSON → Redis String，24h TTL）
- [x] MemoryManager 双路径（Redis 优先 + 内存 dict fallback）
- [x] SessionMemory 序列化（to_dict / from_dict）
- [x] Docker Compose 启动 Redis（redis:7-alpine + AOF 持久化）

### 阶段六：LangChain 迁移 ✅（同步可用，流式调试中）
- [x] LangChain LLM 包装器（ChatOpenAI → DeepSeek API）
- [x] LangChain Tool 迁移（@tool 装饰器替代 BaseTool）
- [x] LangChain Agent（create_react_agent + InMemorySaver）
- [x] 端点暴露（`/agent/langchain/run` + `/agent/langchain/stream`）

### 阶段七：Docker 全项目容器化 ✅
- [x] 后端 Dockerfile（Python 多阶段构建，精简镜像体积）
- [x] 前端 Dockerfile（Node 构建 + nginx:alpine 托管静态文件）
- [x] nginx.conf（SPA fallback + API 反向代理 + SSE 流式支持）
- [x] docker-compose.yml 三服务编排（Redis healthcheck + 启动顺序控制 + 服务互发现）
- [x] .dockerignore（跳过 .venv / node_modules / __pycache__）
- [x] LangChain 依赖补充（langgraph / langchain / langchain-core 加入 requirements.txt）
- [x] config.py Settings 增加 Redis 配置字段（环境变量可覆盖）
- [x] main.py LangChain Agent 懒加载（`_get_langchain_agent()`，降低冷启动耦合）
- [x] `docker compose up -d` 一键启动 → `http://localhost` 全功能可用

### 阶段八：鉴权系统 + 投递看板 + 工程面板 ✅
- [x] JWT 鉴权系统（User 模型 + Repository + bcrypt + python-jose + login/register/refresh 端点）
- [x] 投递看板（Application 模型 + CRUD 端点 + 五列看板视图 + 卡片组件）
- [x] 一键保存到看板（ChatBubble 自动提取公司/岗位/分数 + 手动输入兜底）
- [x] 底部状态栏（Redis 连接指示灯 + Token 消耗进度条 + 限流计数 + Agent 版本切换）
- [x] 聊天记录 localStorage 持久化（刷新后自动恢复，退出登录清除）
- [x] 前端登录/注册页（未登录时显示，登录后进入聊天界面）

### 阶段九：Agent 能力扩展 ✅
- [x] 灵活对话引擎（chat 状态 + ChatNode + chat.md prompt）
- [x] 面试模拟（InterviewTool + interview_service + interview.md，支持 technical/behavioral/mixed）
- [x] 补充 langchain-openai 依赖

### 阶段十：自建评测体系 + 状态栏 + 看板联动 ✅
- [x] Faithfulness 指标（claim extraction + claim verification 两步法）
- [x] AnswerRelevancy 指标（反向生成问题 + n-gram 哈希相似度）
- [x] ContextRecall 指标（关键信息点覆盖检查）
- [x] 5 条评测用例 + 评测执行器 + Markdown 报告生成
- [x] 底部状态栏（Redis 指示灯 + Token 消耗 + 限流 + Agent 版本切换）
- [x] ChatBubble "📌 保存到投递看板" 一键保存（自动提取 + 手动输入兜底）
- [x] Token 计数共享架构（BaseService 支持注入外部 LLMService 实例）

## 2026-08-09 Bug 修复 ✅
- [x] agent_state.py — `_query_mentions_jd` 空函数体 + `wants_resume`/`wants_jd` NameError
- [x] jobpilot_agent.py — `_is_followup` 过激逻辑 + execute/execute_stream 会话保存不一致
- [x] main.py — refresh_token 从 URL 查询参数改为 Body（安全修复）
- [x] evaluation/relevancy.py — 非确定性 hash 改为 hashlib.sha256
- [x] evaluation/runner.py — 评分统计增加 None 检查
- [x] frontend — 实现 token 自动刷新 + 4 个小问题修复（emit、省略号、未用 imports）
- [x] planner.py — 更新过时注释
- [x] prompt_manager.py — 按 key 长度降序替换防止冲突

## 2026-08-14 前端整体改版 + 功能收尾 ✅
- [x] 全宽布局（去掉 840px 居中限制，侧边栏 + 内容区 flex 布局）
- [x] 对话侧边栏（新建对话 + 会话列表 + 删除 + 用户区）
- [x] 多会话数据层（useAgent 重构：conversations 数组 + activeId，标题自动生成）
- [x] 看板四宫格分区（4 活跃状态 2×2 + 已拒底部弱化横条）
- [x] 卡片信息架构（匹配分色阶 + 相对日期 + 备注徽标 + 两行摘要）
- [x] 投递详情编辑弹窗（编辑/创建双模式，暴露全部字段，阶段 pill 按钮）
- [x] 看板新建入口 + 空状态引导
- [x] Toast 消息系统（替换所有 alert/confirm）
- [x] 停止生成按钮（AbortController）+ 复制原文按钮
- [x] 输入框多行（Enter 发送 / Shift+Enter 换行）
- [x] 去除重复的 Agent 切换控件（只保留顶栏）
- [x] 强化 XSS 清洗（svg/math/form/meta 等 + src/xlink:href javascript: 拦截）
- [x] 移除 token/限流状态显示（流式不统计 token + /status 硬编码 0 + nginx 未转发 XFF，投入产出比低，砍掉）

---

## 待完善（质量收尾，非阻塞）

- [x] 面试连续多轮（interview_round 计数器）—— 已在 Phase 11 完成
- [x] 扫描件检测 —— 已在 Phase 11 完成
- [x] ChatBubble 保存按钮状态残留 + useApplications 的 appsError 未展示 —— 已在 Phase 11 完成
- [x] 回归测试 —— Phase 11 做了静态验证，需本地跑 pytest 确认
- [ ] LangChain 流式端点稳定（当前 prebuilt 版有 async/sync 适配 workaround）

---

## 后续开发路径（v0.9.2 → v1.0）

> 按「产品收尾 → 技术纵深 → 上线」四段推进，每段结束都是可演示的里程碑。
> 总时长约 5-6 周。决策：先 RAG 后 MCP；LangGraph 手写图版纳入（成本低，1-2 天）。

### 第一段 · 产品收尾（约 1 周）✅ 已完成（2026-08-14）

| 优先级 | 方向 | 说明 |
|--------|------|------|
| ✅ | 面试连续多轮（interview_round 计数器） | 让面试模拟记住"正在面试中"，不再每轮重新判断路由 |
| ✅ | 扫描件检测 | /upload 提取为空时提示"请上传可编辑 PDF 或粘贴文字" |
| ✅ | 边角清理 | ChatBubble 状态残留、appsError 展示等 review 遗留 |
| 🟡 | 回归测试（本地跑 pytest） | 静态验证已做，需本地执行确认 |

### 第二段 · RAG 检索管线 + 记忆增强 + 产品补全（1-2 周，并列推进）

| 优先级 | 方向 | 说明 |
|--------|------|------|
| 🔴 | Embedding + 向量库 | bge-small-zh-v1.5 本地推理 + Chroma 持久化 |
| 🔴 | Hybrid Search | 向量检索 + BM25 + RRF 融合 |
| 🔴 | Reranker | bge-reranker-base cross-encoder 精排 |
| 🔴 | SearchTool 集成 | 注册进 ToolRegistry，Agent 自动检索知识库 |
| 🔴 | **长期用户画像** | 新增 UserProfile 模型，跨会话沉淀用户技术栈/求职方向/目标公司，持久化到 SQLite |
| 🔴 | **上下文压缩（摘要）** | TokenBudget 增加摘要压缩策略，早期对话 LLM 压缩成摘要替代直接丢弃 |
| 🔴 | **简历库（多简历管理）** | 用户保存多份简历、按岗位切换版本，复用 SQLite + Repository |
| 🔴 | **Alembic 迁移** | 引入数据库迁移（加 UserProfile/Resume 表时不再依赖 create_all） |

> ⚠️ 预警：bge 模型需本地下载数百 MB，Docker Hub / HuggingFace 在国内需提前解决镜像源问题。

> 说明：这一段的四类工作——RAG（知识库检索）、记忆增强（用户画像 + 上下文压缩）、产品补全（简历库）、工程基础（Alembic）——共用同一套 embedding/向量基础设施和 SQLite/Repository 模式，因此并列推进。其中 **Alembic 必须在加 UserProfile/Resume 表之前引入**，避免上线后改 schema 无法迁移。

### 第三段 · MCP 协议接入（1-2 周）

> 方向已定：**先做 MCP Client（让 Agent 调外部工具），MCP Server（暴露自身能力）待定**。

| 优先级 | 方向 | 说明 |
|--------|------|------|
| 🔴 | MCP Client 基础设施 | 用 `mcp` SDK 连 MCP Server，把外部工具动态包装成 BaseTool 注册进 ToolRegistry |
| 🔴 | 接入 GitHub MCP Server | 官方 `@modelcontextprotocol/server-github`（stdio 方式），需 GitHub Personal Access Token（只读即可）。让 Agent 能查目标公司技术栈、面试官开源项目 |
| 🔴 | 接入搜索 MCP Server（Tavily） | 补 RAG 的知识盲区，回答时效性问题（秋招动态、公司近况）。需 Tavily API key（有免费额度） |
| 🔴 | 本地/联网分层路由 | 状态机区分：问知识库类 → 本地 RAG（SearchTool）；问时效性/外部信息 → 联网搜索。体现"RAG + Web Search 混合检索"的权衡 |
| 🟡 | 状态机加外部工具路由 | 检测"XX公司技术栈""面试官项目"→ GitHub 工具；"最新秋招情况"→ 搜索工具 |

**设计要点（面试可讲）**：
- 叙事线：手写 BaseTool → LangChain @tool → MCP Client，体现对工具调用演进的完整理解
- 两个知识来源的分层：本地 RAG（快、零成本、可溯源但有限）vs 联网搜索（时效强但成本高、质量参差），本地优先、联网兜底
- MCP 解决的本质问题：工具碎片化的 N×M 适配问题（每个工具×每个 Agent 都要单独写适配，MCP 统一成 N+M）

**⚠️ 前置确认**：GitHub 连通性已确认 OK。开工前需准备：GitHub PAT（只读）、Tavily API key。

### ~~第三.五段 · LangGraph 手写图版~~（已决定不做）

> **决策（2026-08-16）：不做 LangGraph 手写图版重构。** 理由：项目已经有手写 ReAct + 代码状态机，并且已有 LangGraph prebuilt 版（`create_react_agent`）在跑，再手写 StateGraph 图版只是把同样的东西换成框架语法，边际价值低、没有新增量。手写 ReAct 已经是项目最强的叙事点，不需要用 LangGraph 再证明一遍。若未来投递的岗位 JD 明确要求 LangGraph，再花半天补上即可。

### 第四段 · 工程质量 + 上线收尾（约 1 周）

| 优先级 | 方向 | 说明 |
|--------|------|------|
| 🔴 | 云部署 | 轻量服务器 + Docker Compose + Nginx + HTTPS + 域名，拿公网 URL |
| 🔴 | **测试补强** | 后端关键路径改断言式 pytest（Agent 循环/状态机/TokenBudget），前端核心 composable 加 vitest |
| 🔴 | **CI 自动化** | GitHub Actions：push 自动跑测试 + lint + build（一个 yaml） |
| 🟡 | **可观测性** | 请求 trace id、LLM 调用耗时/费用结构化统计、错误告警 |
| 🟡 | 上线前安全检查 | XSS 升级 DOMPurify、JWT secret 硬化、CORS 收紧 |
| 🟡 | 文档定稿 | 统一 roadmap / changelog / development_log |

### 暂缓 / 视情况

| 方向 | 说明 |
|------|------|
| 多 Agent 协作架构 | 拆简历/JD/检索/决策四 Agent，非主线 |
| 成本工程 / Reflexion 自我反思 | 锦上添花 |
| 云 OCR（VLM 版） | 若需支持拍照上传简历，用 Qwen-VL 走已有 LLM 设施，零新依赖 |
| LoRA 微调 | 需数据集与算力，成本最高，仅特定岗位需要 |
| **面试记录回顾** | 面试模拟结果沉淀 + 评分趋势，与投递看板联动，产品锦上添花 |
| **数据导出** | 投递台账/面试复盘导出 Markdown/PDF |

---

## 手写 ReAct 与 LangChain / LangGraph 的映射关系

> 补充说明：当前 LangChain 版实际用的是 LangGraph prebuilt 的 `create_react_agent`。后续的「LangGraph 手写图版」指放弃 prebuilt，用 StateGraph 手写节点 + conditional_edge。

| 手写实现 | LangChain 对应 | LangGraph 对应 |
|----------|---------------|---------------|
| `BaseTool` | `@tool` 装饰器 | 同左 |
| `LLMService.chat` | `ChatOpenAI.invoke()` | 同左 |
| `Planner.think` 输出 `Plan` | structured output / function calling | — |
| `execute()` 的 for 循环 | `create_react_agent`（prebuilt） | `StateGraph`（手写图） |
| `AgentStateMachine` | — | `conditional_edge` |
| `SessionMemory` | `ConversationBufferMemory` | `state` + `checkpointer` |
| — | — | 并行节点（resume / jd） |
| — | — | `interrupt_before` (human-in-the-loop) |
