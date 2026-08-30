# JobPilot

AI 驱动的求职助手——从零手写 ReAct Agent，覆盖简历分析、JD 解析、人岗匹配、模拟面试、知识库问答、投递看板全流程。

> 当前版本：**v0.9.5**

## Tech Stack

- **后端**：Python 3.11 / FastAPI / SQLAlchemy / Redis / Alembic
- **AI Agent**：手写 ReAct Agent（Planner + 代码状态机 + Tool + Memory）+ LangChain 双版本并行
- **RAG**：通义千问 text-embedding-v3 + BM25 + RRF 混合检索 + 分块/重排分层 + 拒答阈值
- **MCP**：接入 GitHub MCP Client（只读白名单），外部工具与本地 RAG 分层
- **前端**：Vue 3（Vite + Composition API）
- **文档解析**：PyMuPDF（PDF）+ python-docx（DOCX）
- **流式输出**：Server-Sent Events (SSE)
- **容器化**：Docker / Docker Compose（Redis + 后端 + Nginx 前端）

## 核心能力

### Agent 架构

- **手写 ReAct Agent**：从零实现 Reason→Act→Observe 循环，不依赖 LangChain；代码状态机（AgentStateMachine）确定性控制 Agent 决策，LLM 仅做语义选择
- **LangChain 版并行**：ChatOpenAI + @tool + create_react_agent，与手写版同输入同输出对比
- **MCP Client**：接入 GitHub MCP Server，动态包装为 BaseTool 注册进 ToolRegistry；只读白名单过滤写操作工具
- **三层记忆**：Redis 会话记忆（24h TTL + 优雅降级）+ SQLite 用户画像（跨会话持久化）+ LLM 摘要压缩（长对话失忆解决）
- **RAG 检索管线**：Embedding + 纯 Python 向量存储 + BM25，RRF 融合；57 篇知识库；来源标注代码强制（可溯源）；分块/重排分层 + 拒答阈值

### 产品功能

- 简历分析 / JD 解析 / 人岗匹配
- 模拟面试（技术 / 行为 / 综合三模式，多轮追问）
- 知识库问答（后端 / Agent / 前端 / 算法 / 产品 / 测试 / 求职通用）
- RAG 混合检索（非对称 embedding + BM25 + RRF + 分块/重排分层 + 来源溯源）
- 多简历管理（按岗位切换版本）
- 求职画像（Agent 跨对话记住你的目标岗位 / 技术栈）
- 投递看板（5 阶段跟踪）+ 多会话管理

### 工程质量

- 115 个后端 pytest + 18 个前端 vitest（覆盖状态机路由、TokenBudget、RAG 检索、MCP 适配、Agent 容错）
- 自建 56 条多类别带标注 RAG 评测集（recall@1 / MRR / NDCG 对比三种检索配置，见 docs/rag_eval.md）
- JWT 双 token 鉴权（access 30min / refresh 7d）+ 固定窗口限流（20 req/min）
- Alembic 数据库迁移 + Docker Compose 三服务容器化 + GitHub Actions CI

## Quick Start

```bash
# 方式一：Docker 一键启动（推荐）
docker compose up -d --build

# 打开 http://localhost:5173 或 http://localhost:80

# 方式二：本地开发
# 1. 启动 Redis + 后端
docker compose up -d redis backend

# 2. 前端用 Vite（热更新）
cd frontend
npm run dev -- --port 5199

# 打开 http://localhost:5199
```

首次使用需配置环境变量：

```bash
cp backend/.env.example backend/.env
# 编辑 backend/.env，填入 DeepSeek API Key 和 DashScope API Key
# 可选：填入 GITHUB_PAT 启用 MCP（GitHub 工具，只读 PAT 即可）
```

## API Endpoints

| 端点 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 健康检查 |
| `/status` | GET | 系统状态快照 |
| `/auth/register` | POST | 用户注册 |
| `/auth/login` | POST | 登录（返回 access + refresh token） |
| `/auth/refresh` | POST | 刷新 access token |
| `/agent/run` | POST | 手写版 Agent（同步） |
| `/agent/run/stream` | POST | 手写版 Agent（SSE 流式） |
| `/agent/langchain/run` | POST | LangChain 版 Agent（同步） |
| `/agent/langchain/stream` | POST | LangChain 版 Agent（SSE 流式） |
| `/upload` | POST | 文件摄入（PDF / DOCX） |
| `/applications` | GET/POST | 投递记录列表 / 创建 |
| `/applications/{id}` | PUT/DELETE | 投递记录更新 / 删除 |
| `/resumes` | GET/POST | 简历库列表 / 创建 |
| `/resumes/{id}` | PUT/DELETE | 简历更新 / 删除 |
| `/profile` | GET/PUT | 用户画像获取 / 更新 |

## Docs

- [架构设计](docs/architecture.md)
- [API 设计](docs/api_design.md)
- [技术蓝图](docs/roadmap.md)
- [RAG 评测与工程化](docs/rag_eval.md)
- [变更日志](docs/changelog.md)
- [开发日志](docs/development_log.md)
