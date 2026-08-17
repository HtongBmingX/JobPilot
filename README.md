# JobPilot

An AI Agent for Intelligent Job Hunting.

> 当前版本：**v0.6.0** — Redis 持久化 + LangChain 迁移 · [完整开发框架](docs/development_framework.md)

## Tech Stack

- **后端**：Python / FastAPI / DeepSeek API
- **AI 框架**：手写 ReAct Agent + LangChain 双版本并行
- **前端**：Vue3（Vite + Composition API）
- **文档解析**：PyMuPDF（PDF）+ python-docx（DOCX）
- **流式输出**：Server-Sent Events (SSE)
- **缓存 / 限流**：Redis (Docker)
- **容器化**：Docker / Docker Compose

## Architecture

- **手写 ReAct Agent**（Planner + AgentStateMachine + Tool + Memory + TokenBudget）
- **LangChain 版本**（ChatOpenAI + @tool + create_react_agent + InMemorySaver）—— 与手写版并行，同输入同输出
- 流式输出链路：`chat_stream()` → `execute_stream()` → `StreamingResponse (SSE)` → `fetch + ReadableStream`
- 多轮对话：`SessionMemory.messages` + `TokenBudget` 控制器
- 会话持久化：Redis + 内存 fallback 双路径
- API 限流：固定窗口算法（Redis INCR + EXPIRE）

## Quick Start

```bash
# 1. 启动 Redis
docker compose up -d

# 2. 启动后端
cd "D:\py project\JobPilot"
.venv\Scripts\python.exe -m uvicorn backend.main:app --reload

# 3. 启动前端（另一个终端）
cd frontend
npm run dev

# 4. 打开 http://localhost:5173
```

## API Endpoints

| 端点 | 方法 | 说明 |
|------|------|------|
| `/agent/run` | POST | 手写版 Agent（同步） |
| `/agent/run/stream` | POST | 手写版 Agent（SSE 流式） |
| `/agent/langchain/run` | POST | LangChain 版 Agent（同步） |
| `/agent/langchain/stream` | POST | LangChain 版 Agent（SSE 流式） |
| `/upload` | POST | 文件摄入 |

## Features

- 手写 ReAct Agent + LangChain 双版本并行（同输入可对比输出）
- 代码状态机（AgentStateMachine）—— 确定性控制 Agent 决策
- SSE 流式输出 + 思考链可视化 + Markdown 渲染
- 多轮对话（Token 预算控制 + 对话历史）
- AI 简历分析 / JD 分析 / 岗位匹配
- 文件摄入（PDF / DOCX 上传解析）
- Redis 会话持久化 + 优雅降级
- API 限流（固定窗口，每 IP 每端点独立计数）
- Docker Compose 一键启动 Redis
- 自定义异常体系 + 全局错误处理

## Docs

- [开发框架](docs/development_framework.md)
- [架构设计](docs/architecture.md)
- [API 设计](docs/api_design.md)
- [变更日志](docs/changelog.md)
- [开发日志](docs/development_log.md)
