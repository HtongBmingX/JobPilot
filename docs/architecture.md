# JobPilot Architecture（v0.6.0）

> 最后更新：2026-07-23

## 整体架构

```
                        用户界面（Vue3 SPA）
                              │
                              │ fetch / SSE
                              ▼
                     FastAPI 入口（main.py）
                    ╔═══════════════════════╗
                    ║  CORS 中间件           ║
                    ║  API 限流（Rate Limiter）║
                    ║  Error Handlers        ║
                    ╚═══════════════════════╝
                              │
               ┌──────────────┼──────────────┐
               ▼              ▼              ▼
        手写 ReAct Agent  LangChain Agent   文件摄入
        (/agent/run)      (/agent/langchain) (/upload)
               │              │              │
               │              │              ▼
               │              │         IngestTool (PDF/DOCX)
               │              │
               │    ┌────────┴────────┐
               │    │ ChatOpenAI      │
               │    │ create_react_agent│
               │    │ @tool × 3       │
               │    │ InMemorySaver   │
               │    └─────────────────┘
               │
     ┌─────────┼─────────┐
     ▼                   ▼
  Planner          AgentStateMachine
  (LLM 语义判断)     (代码确定性规则)
     │                   │
     └───────┬───────────┘
             │ 决策：允许哪些 action
             ▼
        ToolRegistry ──► Tool ──► Service ──► PromptManager ──► LLMService ──► DeepSeek API
             │
             ▼ 结果写回
        SessionMemory (业务记忆 + 对话记忆)
             │
             ├── TokenBudget (token 配额管理)
             │
             ▼
        MemoryManager ──► Redis (优先) / 内存 dict (fallback)
                              │
                              ▼
                         Redis 持久化 + 24h TTL
```

---

## 核心设计决策

### 1. 双 Agent 架构（手写 + LangChain 并行）

| 层级 | 手写版 | LangChain 版 |
|------|--------|-------------|
| LLM 调用 | `LLMService.chat()` | `ChatOpenAI.invoke()` |
| 流式输出 | `LLMService.chat_stream()` | `ChatOpenAI.stream()` |
| Tool 定义 | `BaseTool` 抽象类 | `@tool` 装饰器 |
| 决策器 | `Planner.think()` | `create_react_agent()` 内置 |
| 状态管理 | `AgentStateMachine`（代码）| LangGraph conditional_edge |
| 记忆 | `SessionMemory` + `MemoryManager` | `InMemorySaver` (checkpointer) |

**为什么并存**：手写版验证了对 Agent 本质的理解，LangChain 版验证了理解和框架的一致性。面试时可以当面对比两个版本的输出。

### 2. 状态机代码化（AgentStateMachine）

**旧（prompt 驱动）**：planner.md 用自然语言描述「resume → jd → match → finish」规则，依赖 LLM 遵守

**新（代码驱动）**：AgentStateMachine.compute_allowed_actions() 确定性返回当前允许的合法 action。效果：
- 单 Tool 请求 → 跳过 LLM 决策，直接执行（零延迟、零 token）
- 多 Tool 请求 → LLM 判断优先顺序（保留语义理解）
- 已完成的 Tool 不可重复执行（规则由代码保证，不受 LLM 影响）

### 3. 优雅降级（Redis 双路径）

```
MemoryManager
  ├── Redis 可用 → RedisSessionStore（持久化 + 多进程共享 + TTL 自动过期）
  └── Redis 不可用 → 内存 dict（功能正常，重启丢数据）

Rate Limiter
  ├── Redis 可用 → 固定窗口限流（INCR + EXPIRE）
  └── Redis 不可用 → 放行所有请求（安全让位可用性）
```

---

## 数据流（一次完整的用户请求）

```
1. 用户上传简历 PDF → /upload → IngestTool → 提取纯文本
2. 用户提问 "分析我的简历" → /agent/run/stream
3. FastAPI 限流检查（固定窗口）
4. Agent 接收请求 → MemoryManager.create_session(session_id)
5. TokenBudget 从对话历史中截取近期消息
6. AgentStateMachine 计算允许的 action → ["resume"]
7. ResumeTool.run(resume=...) → ResumeService.analyze() → LLMService.chat() → DeepSeek API
8. 结果写入 SessionMemory.resume_analysis
9. AgentStateMachine 再次计算 → ["finish"]
10. Synthesize（基于 resume_analysis + conversation_history）→ LLMService.chat_stream()
11. SSE 逐 token 推送 → 前端 ChatBubble 实时渲染 + ThinkChain 展示步骤
12. MemoryManager.save_session() → Redis SETEX（24h TTL）
```

---

## 前端组件树

```
App.vue
├── ChatBubble × N          ← 对话气泡（user/assistant 区分 + Markdown 渲染）
├── ThinkChain              ← 思考链（⏳ 正在分析简历 / ✅ 已完成简历分析）
├── InputPanel              ← 输入面板
│   ├── 文件上传（PDF/DOCX）
│   ├── 简历文本编辑
│   ├── JD 文本编辑
│   └── 问题输入 + 发送按钮
└── useAgent (composable)   ← 状态管理（messages, thinkSteps, loading, error, sessionId）
```

---

## 下一阶段

- 前端版 LangChain 切换按钮
- LangGraph 重构（并行节点 + conditional_edge + human-in-the-loop）
- 云部署（Docker 全项目容器化 → 云服务器）
- 评测体系（faithfulness / answer relevancy / context recall）
- RAG 长期记忆（bge-small-zh embedding + Chroma 向量存储）
